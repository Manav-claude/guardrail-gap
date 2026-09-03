#!/usr/bin/env python
"""Build the AGGREGATE result files that accompany the paper, from the cached
per-turn shards. Everything written here is a rate, count, or definition -
no conversation text - so results_public/ is safe to publish alongside code.

Files (results_public/):
  table2_commercial_ci.csv      CDR by product x family x config (last/full/m2s) with Wilson 95% CIs, FPR with CI
  tableA_reference_ci.csv       same for the open reference tier
  gap_decomposition_{commercial,reference}.csv  GMG(last->full), McNemar p, config-/model-induced terms, AUROC
  detector_<product>_<cfg>.csv  per-internal-detector detection by family + FPR (4 commercial products, last & full)
  strength_curve.csv            CDR/FPR at every reconstructed filter strength (Bedrock, Model Armor, Azure text)
  per_decision_final_turn.csv   single-decision (final-turn) fire rates, last vs full, attacks and benign
  cross_product_evasion.csv     attacks missed by all four commercial products
  gap_by_length.csv             CDR last/full by n_turns bin
  product_agreement.csv         pairwise Jaccard / phi of detected sets
  latency_cost.csv              median/p95 latency, billing units, coverage<1 counts
  bedrock_denied_topics.json    the eight author-defined topic definitions

Run:  python scripts/make_public_results.py
"""
from __future__ import annotations
import sys, pathlib, sqlite3, json, math, itertools, csv
import numpy as np, pandas as pd
from scipy.stats import chi2, mannwhitneyu, spearmanr
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from guardgap import runner  # noqa: E402
from guardgap.report import _detectors_from_raw  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results_public"
FAM = ["escalation", "drift", "coreference"]
CFG = ["last", "full", "m2s"]
COM = ["bedrock", "azure_prompt_shields", "azure_text", "model_armor"]
REF = ["protectai_deberta", "qwen3guard", "prompt_guard2"]


def load(p: str) -> pd.DataFrame | None:
    path = runner.shard_path(p)
    if not path.exists():
        return None
    con = sqlite3.connect(path)
    d = pd.read_sql_query("select conv_id,label,family,config,turn,n_turns,blocked,r,latency_ms,"
                          "cost_units,coverage,raw_json from scores", con)
    con.close()
    d["family"] = d["family"].fillna("none")
    return d


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = (z / d) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, c - h), min(1.0, c + h)


def mcnemar(b: int, c: int) -> float:
    n = b + c
    return 1.0 if n == 0 else float(chi2.sf((abs(b - c) - 1) ** 2 / n, 1))


def conv_table(d: pd.DataFrame) -> pd.DataFrame:
    return d.groupby(["conv_id", "label", "family", "config"]).agg(
        det=("blocked", "max"), maxr=("r", "max"), n_turns=("n_turns", "max")).reset_index()


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {name} ({len(rows)} rows)")


def cdr_ci_table(products: list[str], name: str, D: dict) -> None:
    rows = []
    for p in products:
        c = conv_table(D[p])
        for cfg in CFG:
            row = {"product": p, "config": cfg}
            for f in FAM:
                a = c[(c.label == "attack") & (c.family == f) & (c.config == cfg)]
                r, lo, hi = wilson(int(a.det.sum()), len(a))
                row[f"{f}_cdr"] = f"{r:.4f}"; row[f"{f}_lo"] = f"{lo:.4f}"; row[f"{f}_hi"] = f"{hi:.4f}"; row[f"{f}_n"] = len(a)
            b = c[(c.label == "benign") & (c.config == cfg)]
            r, lo, hi = wilson(int(b.det.sum()), len(b))
            row.update({"fpr": f"{r:.4f}", "fpr_lo": f"{lo:.4f}", "fpr_hi": f"{hi:.4f}", "benign_n": len(b)})
            rows.append(row)
    write_csv(name, rows)


def gap_table(products: list[str], D: dict, name: str = "gap_decomposition.csv") -> None:
    rows = []
    for p in products:
        c = conv_table(D[p]); a = c[c.label == "attack"]
        piv = a.pivot_table(index="conv_id", columns="config", values="det").dropna(subset=["last", "full"])
        b = int(((piv["last"] == 1) & (piv["full"] == 0)).sum()); cc = int(((piv["last"] == 0) & (piv["full"] == 1)).sum())
        gmg = float(piv["full"].mean() - piv["last"].mean())
        def auroc(cfg):
            pos = c[(c.label == "attack") & (c.config == cfg)].maxr.values
            neg = c[(c.label == "benign") & (c.config == cfg)].maxr.values
            return mannwhitneyu(pos, neg, alternative="greater").statistic / (len(pos) * len(neg)) if len(pos) and len(neg) else float("nan")
        rows.append({"product": p, "n": len(piv), "cdr_last": f"{piv['last'].mean():.4f}", "cdr_full": f"{piv['full'].mean():.4f}",
                     "gmg_last_to_full": f"{gmg:+.4f}", "mcnemar_p": f"{mcnemar(b, cc):.3g}", "only_last": b, "only_full": cc,
                     "config_induced": f"{gmg:+.4f}", "model_induced": f"{1 - piv['full'].mean():.4f}",
                     "auroc_last": f"{auroc('last'):.4f}", "auroc_full": f"{auroc('full'):.4f}"})
    write_csv(name, rows)


def detector_tables(D: dict) -> None:
    for p in COM:
        d = D[p]
        for cfg in ("last", "full"):
            sub = d[d.config == cfg]
            fired: dict = {}; meta: dict = {}
            for row in sub.itertuples():
                if not row.raw_json:
                    continue
                try:
                    raw = json.loads(row.raw_json)
                except ValueError:
                    continue
                meta[row.conv_id] = (row.label, row.family)
                for name, fire, _ in _detectors_from_raw(p, raw):
                    fired[(row.conv_id, name)] = fired.get((row.conv_id, name), False) or fire
            dets = sorted({n for (_, n) in fired})
            rows = []
            for det in dets:
                r = {"detector": det}
                for f in FAM:
                    ids = [c for c, (l, ff) in meta.items() if l == "attack" and ff == f]
                    r[f] = f"{sum(fired.get((c, det), False) for c in ids) / len(ids):.4f}" if ids else ""
                bids = [c for c, (l, _) in meta.items() if l == "benign"]
                r["fpr"] = f"{sum(fired.get((c, det), False) for c in bids) / len(bids):.4f}" if bids else ""
                rows.append(r)
            write_csv(f"detector_{p}_{cfg}.csv", rows)


def strength_curve(D: dict) -> None:
    def bed(raw, ok, topics=True):
        r = json.loads(raw) if raw else {}
        f = any(x["detected"] and x["confidence"] in ok for x in r.get("filters", []))
        t = topics and any(x["detected"] for x in r.get("topics", []))
        return int(bool(f or t))
    def ma(raw, levels):
        r = json.loads(raw) if raw else {}; fr = r.get("filterResults", {}); hits = []
        rai = fr.get("rai", {}).get("raiFilterResult", {}).get("raiFilterTypeResults", {})
        for v in rai.values():
            hits.append(v.get("matchState") == "MATCH_FOUND" and v.get("confidenceLevel") in levels)
        pj = fr.get("pi_and_jailbreak", {}).get("piAndJailbreakFilterResult", {})
        hits.append(pj.get("matchState") == "MATCH_FOUND" and pj.get("confidenceLevel") in levels)
        for k in ("malicious_uris", "csam"):
            x = fr.get(k, {}); inner = list(x.values())[0] if x else {}
            hits.append(isinstance(inner, dict) and inner.get("matchState") == "MATCH_FOUND")
        return int(any(hits))
    def az(raw, thr):
        r = json.loads(raw) if raw else {}
        return int(any(c["severity"] >= thr for c in r.get("categoriesAnalysis", [])))
    specs = [
        ("bedrock", "HIGH (+topics, as run)", lambda r: bed(r, {"LOW", "MEDIUM", "HIGH"})),
        ("bedrock", "MEDIUM (+topics)", lambda r: bed(r, {"MEDIUM", "HIGH"})),
        ("bedrock", "LOW (+topics)", lambda r: bed(r, {"HIGH"})),
        ("bedrock", "HIGH content-only", lambda r: bed(r, {"LOW", "MEDIUM", "HIGH"}, False)),
        ("bedrock", "MEDIUM content-only", lambda r: bed(r, {"MEDIUM", "HIGH"}, False)),
        ("bedrock", "LOW content-only", lambda r: bed(r, {"HIGH"}, False)),
        ("model_armor", "LOW_AND_ABOVE (as run)", lambda r: ma(r, {"LOW_AND_ABOVE", "MEDIUM_AND_ABOVE", "HIGH"})),
        ("model_armor", "MEDIUM_AND_ABOVE", lambda r: ma(r, {"MEDIUM_AND_ABOVE", "HIGH"})),
        ("model_armor", "HIGH", lambda r: ma(r, {"HIGH"})),
        ("azure_text", "severity>=2 (as run)", lambda r: az(r, 2)),
        ("azure_text", "severity>=4 (vendor default)", lambda r: az(r, 4)),
        ("azure_text", "severity>=6", lambda r: az(r, 6)),
    ]
    rows = []
    for p, label, fn in specs:
        d = D[p].copy(); d["f"] = d.raw_json.map(fn)
        c = d.groupby(["conv_id", "label", "family", "config"]).f.max().reset_index()
        for cfg in ("last", "full", "m2s"):
            a = c[(c.label == "attack") & (c.config == cfg)]; b = c[(c.label == "benign") & (c.config == cfg)]
            if a.empty:
                continue
            row = {"product": p, "strength": label, "config": cfg, "cdr_pooled": f"{a.f.mean():.4f}"}
            for f in FAM:
                row[f] = f"{a[a.family == f].f.mean():.4f}"
            row["fpr"] = f"{b.f.mean():.4f}"
            rows.append(row)
    write_csv("strength_curve.csv", rows)


def per_decision(D: dict) -> None:
    rows = []
    for p in COM + REF:
        d = D[p]; fin = d[(d.turn == d.n_turns) & d.config.isin(["last", "full"])]
        for label in ("attack", "benign"):
            piv = fin[fin.label == label].pivot_table(index="conv_id", columns="config", values="blocked").dropna()
            b = int(((piv["last"] == 1) & (piv["full"] == 0)).sum()); c = int(((piv["last"] == 0) & (piv["full"] == 1)).sum())
            rows.append({"product": p, "label": label, "n": len(piv), "final_turn_rate_last": f"{piv['last'].mean():.4f}",
                         "final_turn_rate_full": f"{piv['full'].mean():.4f}", "only_last": b, "only_full": c,
                         "mcnemar_p": f"{mcnemar(b, c):.3g}"})
    write_csv("per_decision_final_turn.csv", rows)


def evasion_agreement(D: dict) -> None:
    det = {p: conv_table(D[p]) for p in COM}
    piv = {p: det[p][det[p].label == "attack"].pivot_table(index=["conv_id", "family"], columns="config", values="det") for p in COM}
    idx = piv["bedrock"].index
    for p in COM:
        idx = idx.intersection(piv[p].index)
    fam = pd.Series([i[1] for i in idx], index=idx)
    rows = []
    for cfgs, name in [(["last"], "last"), (["last", "full", "m2s"], "any_config")]:
        caught = pd.DataFrame({p: piv[p].loc[idx][cfgs].max(axis=1) for p in COM})
        miss = caught.sum(axis=1) == 0
        row = {"configs": name, "n_attacks": len(idx), "missed_by_all4": int(miss.sum()), "missed_by_all4_rate": f"{miss.mean():.4f}",
               "caught_by_exactly_one_rate": f"{(caught.sum(axis=1) == 1).mean():.4f}"}
        for f in FAM:
            row[f"missed_all4_{f}"] = f"{miss[fam == f].mean():.4f}"
        rows.append(row)
    write_csv("cross_product_evasion.csv", rows)
    caught = pd.DataFrame({p: piv[p].loc[idx]["last"] for p in COM})
    rows = []
    for p1, p2 in itertools.combinations(COM, 2):
        x = caught[p1].values; y = caught[p2].values
        inter = int(((x == 1) & (y == 1)).sum()); uni = int(((x == 1) | (y == 1)).sum())
        phi = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float("nan")
        rows.append({"product_a": p1, "product_b": p2, "jaccard_detected_last": f"{inter / max(1, uni):.4f}", "phi": f"{phi:.4f}"})
    write_csv("product_agreement.csv", rows)


def gap_by_length(D: dict) -> None:
    rows = []
    for p in COM + REF:
        c = conv_table(D[p]); a = c[c.label == "attack"]
        piv = a.pivot_table(index=["conv_id", "n_turns", "family"], columns="config", values="det").reset_index()
        for lo, hi in [(2, 3), (4, 5), (6, 8), (9, 999)]:
            s = piv[(piv.n_turns >= lo) & (piv.n_turns <= hi)]
            if len(s):
                rows.append({"product": p, "n_turns_bin": f"{lo}-{hi if hi < 999 else '+'}", "n": len(s),
                             "cdr_last": f"{s['last'].mean():.4f}", "cdr_full": f"{s['full'].mean():.4f}",
                             "gap": f"{s['full'].mean() - s['last'].mean():+.4f}"})
        rho, pv = spearmanr(piv.n_turns, piv["full"] - piv["last"])
        rows.append({"product": p, "n_turns_bin": "spearman(n_turns, gap)", "n": len(piv), "cdr_last": "", "cdr_full": "", "gap": f"rho={rho:+.4f} p={pv:.3g}"})
    write_csv("gap_by_length.csv", rows)


def latency_cost(D: dict) -> None:
    rows = []
    for p in COM + REF:
        d = D[p]
        for cfg in CFG:
            s = d[d.config == cfg]
            if s.empty:
                continue
            rows.append({"product": p, "config": cfg, "calls": len(s), "latency_ms_median": f"{s.latency_ms.median():.0f}",
                         "latency_ms_p95": f"{s.latency_ms.quantile(0.95):.0f}", "cost_units_total": f"{s.cost_units.clip(lower=0).sum():.0f}",
                         "calls_coverage_lt_1": int((s.coverage < 1).sum())})
    write_csv("latency_cost.csv", rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    D = {p: load(p) for p in COM + REF}
    missing = [p for p, d in D.items() if d is None]
    if missing:
        print("no cached run for:", missing)
    D = {p: d for p, d in D.items() if d is not None}
    com = [p for p in COM if p in D]; ref = [p for p in REF if p in D]
    if com:
        cdr_ci_table(com, "table2_commercial_ci.csv", D)
        gap_table(com, D, "gap_decomposition_commercial.csv")
        if all(p in D for p in COM):
            detector_tables(D); strength_curve(D); evasion_agreement(D)
    if ref:
        cdr_ci_table(ref, "tableA_reference_ci.csv", D)
        gap_table(ref, D, "gap_decomposition_reference.csv")
    per_decision(D); gap_by_length(D); latency_cost(D)
    try:
        sys.path.insert(0, str(ROOT / "infra"))
        from aws_provision_guardrail import TOPICS  # type: ignore
        (OUT / "bedrock_denied_topics.json").write_text(
            json.dumps([{"name": n, "definition": d, "type": "DENY"} for n, d in TOPICS], indent=1), encoding="utf-8")
        print("wrote bedrock_denied_topics.json")
    except Exception as e:  # noqa: BLE001
        print("topics not written:", e)


if __name__ == "__main__":
    main()
