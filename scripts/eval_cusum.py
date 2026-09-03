#!/usr/bin/env python
"""Stateful-adapter evaluation (paper Section V-G): wrap each detector's own
per-turn scores in a CUSUM accumulator and compare, AT A MATCHED BENIGN
FALSE-POSITIVE BUDGET, against the best single per-turn threshold.

For every product with a cached run (config = last) and each budget:
  * per-turn rule:  conversation fires iff max_t r_t >= thr; thr is the value
    with the largest attack CDR whose benign FPR <= budget (None if no
    threshold meets the budget, e.g. Bedrock's coarse confidence levels).
  * CUSUM rule:     S_t = max(0, S_{t-1} + r_t - delta); fire iff S_t > h;
    (delta, h) chosen from a small grid as the pair with the largest attack
    CDR whose benign FPR <= budget. Calibration uses all benign conversations
    (no held-out split), which is stated in the paper.

Writes results_public/cusum_matched_budget.csv and prints the table.
Run:  python scripts/eval_cusum.py
"""
from __future__ import annotations
import sys, pathlib, sqlite3, csv
import numpy as np, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from guardgap import runner  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "results_public"
PRODUCTS = ["bedrock", "azure_prompt_shields", "azure_text", "model_armor",
            "protectai_deberta", "qwen3guard", "prompt_guard2"]
BUDGETS = (0.05, 0.01)
DELTAS = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.33, 0.5]
HS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]


def streams(product: str):
    path = runner.shard_path(product)
    if not path.exists():
        return None
    con = sqlite3.connect(path)
    d = pd.read_sql_query("select conv_id,label,turn,r from scores where config='last'", con)
    con.close()
    d = d.sort_values(["conv_id", "turn"])
    return {cid: (g.label.iloc[0], g.r.values) for cid, g in d.groupby("conv_id")}


def cusum_fire(r, delta, h) -> int:
    s = 0.0
    for x in r:
        s = max(0.0, s + x - delta)
        if s > h:
            return 1
    return 0


def evaluate(product: str, rows: list[dict]) -> None:
    g = streams(product)
    if not g:
        return
    att = [v[1] for v in g.values() if v[0] == "attack"]
    ben = [v[1] for v in g.values() if v[0] == "benign"]
    if not att or not ben:
        return
    thresholds = sorted({float(x) for r in g.values() for x in np.round(r[1], 4) if x > 0})
    for budget in BUDGETS:
        best = None
        for t in thresholds:
            fpr = float(np.mean([r.max() >= t for r in ben]))
            if fpr <= budget:
                cdr = float(np.mean([r.max() >= t for r in att]))
                if best is None or cdr > best[1]:
                    best = (t, cdr, fpr)
        bc = None
        for delta in DELTAS:
            for h in HS:
                fpr = float(np.mean([cusum_fire(r, delta, h) for r in ben]))
                if fpr <= budget:
                    cdr = float(np.mean([cusum_fire(r, delta, h) for r in att]))
                    if bc is None or cdr > bc[2]:
                        bc = (delta, h, cdr, fpr)
        row = {"product": product, "budget": budget,
               "perturn_thr": best[0] if best else "", "perturn_cdr": f"{best[1]:.3f}" if best else "",
               "perturn_fpr": f"{best[2]:.3f}" if best else "",
               "cusum_delta": bc[0] if bc else "", "cusum_h": bc[1] if bc else "",
               "cusum_cdr": f"{bc[2]:.3f}" if bc else "", "cusum_fpr": f"{bc[3]:.3f}" if bc else ""}
        rows.append(row)
        print(f"{product:20} budget {budget:.0%}: per-turn "
              f"{'CDR=%.3f FPR=%.3f (thr %.3g)' % (best[1], best[2], best[0]) if best else 'no threshold meets budget'}"
              f" | CUSUM {'CDR=%.3f FPR=%.3f (d=%g,h=%g)' % (bc[2], bc[3], bc[0], bc[1]) if bc else 'none'}")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows: list[dict] = []
    for p in PRODUCTS:
        evaluate(p, rows)
    if rows:
        with open(OUT / "cusum_matched_budget.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"\nwrote {OUT / 'cusum_matched_budget.csv'}")


if __name__ == "__main__":
    main()
