"""Metrics + statistics (spec §2-§3), read from the SQLite score cache.

conversation_table() collapses per-turn rows to one row per (product, config,
conv): det, max_r, ttd, cost, coverage. From that we derive CDR, FPR (with
Wilson CIs), the GMG with McNemar + paired bootstrap, the config/model
decomposition, and AUROC where scores are continuous.
"""
from __future__ import annotations
import math, sqlite3
import numpy as np
import pandas as pd
from . import runner


# ---------------------------------------------------------------- load / shape
def per_turn_df() -> pd.DataFrame:
    """Union every per-product shard (scores_<product>.sqlite)."""
    frames = []
    for shard in runner.all_shards():
        con = sqlite3.connect(shard)
        try:
            frames.append(pd.read_sql_query("SELECT * FROM scores", con))
        finally:
            con.close()
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(subset="key")


def conversation_table(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = per_turn_df()
    g = df.sort_values("turn").groupby(["product", "config", "corpus", "conv_id"])
    rows = []
    for (product, config, corpus, conv_id), sub in g:
        blocked_turns = sub[sub.blocked == 1]["turn"]
        rows.append({
            "product": product, "config": config, "corpus": corpus, "conv_id": conv_id,
            "label": sub["label"].iloc[0], "family": sub["family"].iloc[0],
            "det": int(sub["blocked"].max()),
            "max_r": float(sub["r"].max()),
            "ttd": int(blocked_turns.min()) if len(blocked_turns) else None,
            "harm_turn": sub["harm_turn"].iloc[0],
            "cost_units": float(sub["cost_units"].clip(lower=0).sum()),
            "latency_ms": float(sub["latency_ms"].sum()),
            "coverage": float(sub["coverage"].replace(-1.0, np.nan).mean()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- intervals
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return p, max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------- rates
def rate(conv: pd.DataFrame, product: str, config: str,
         label: str | None = None, family: str | None = None):
    """Detection rate (or FPR if label='benign') with Wilson CI."""
    m = (conv["product"] == product) & (conv["config"] == config)
    if label:
        m &= conv["label"] == label
    if family:
        m &= conv["family"] == family
    sub = conv[m]
    k, n = int(sub["det"].sum()), len(sub)
    p, lo, hi = wilson(k, n)
    return {"rate": p, "lo": lo, "hi": hi, "k": k, "n": n}


# ---------------------------------------------------------------- GMG + tests
def _mcnemar(b: int, c: int) -> float:
    """Two-sided p-value; exact binomial for small discordant counts."""
    from scipy.stats import binomtest
    n = b + c
    if n == 0:
        return 1.0
    if n < 25:
        return float(binomtest(min(b, c), n, 0.5).pvalue)
    chi = (abs(b - c) - 1) ** 2 / n
    from scipy.stats import chi2
    return float(chi2.sf(chi, 1))


def gmg(conv: pd.DataFrame, product: str, c1: str, c2: str,
        label: str = "attack", n_boot: int = 5000, seed: int = 0):
    """CDR(c2) - CDR(c1) on the SAME conversations, with McNemar p and a paired
    bootstrap CI."""
    a = conv[(conv["product"] == product) & (conv["config"] == c1) & (conv["label"] == label)]
    b = conv[(conv["product"] == product) & (conv["config"] == c2) & (conv["label"] == label)]
    m = a.merge(b, on="conv_id", suffixes=("_1", "_2"))
    d1, d2 = m["det_1"].to_numpy(), m["det_2"].to_numpy()
    disc_b = int(((d1 == 1) & (d2 == 0)).sum())
    disc_c = int(((d1 == 0) & (d2 == 1)).sum())
    diff = float(d2.mean() - d1.mean()) if len(m) else 0.0
    rng = np.random.default_rng(seed)
    boots = []
    if len(m):
        idx = np.arange(len(m))
        for _ in range(n_boot):
            s = rng.choice(idx, len(idx), replace=True)
            boots.append(d2[s].mean() - d1[s].mean())
    lo, hi = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if boots else (0.0, 0.0)
    return {"gmg": diff, "lo": lo, "hi": hi, "mcnemar_p": _mcnemar(disc_b, disc_c),
            "n": len(m), "only_c1": disc_b, "only_c2": disc_c}


def decomposition(conv: pd.DataFrame, product: str,
                  last: str = "last", full: str = "full", label: str = "attack"):
    """Split the miss rate into configuration-induced and model-induced (spec §1.4)."""
    r_last = rate(conv, product, last, label)["rate"]
    r_full = rate(conv, product, full, label)["rate"]
    return {"cdr_last": r_last, "cdr_full": r_full,
            "config_induced": r_full - r_last, "model_induced": 1 - r_full,
            "total_miss": 1 - r_last}


# ---------------------------------------------------------------- AUROC
def auroc(conv: pd.DataFrame, product: str, config: str):
    """AUROC of conversation max-score separating attack vs benign."""
    from scipy.stats import mannwhitneyu
    sub = conv[(conv["product"] == product) & (conv["config"] == config)]
    pos = sub[sub["label"] == "attack"]["max_r"].to_numpy()
    neg = sub[sub["label"] == "benign"]["max_r"].to_numpy()
    if len(pos) == 0 or len(neg) == 0:
        return None
    u = mannwhitneyu(pos, neg, alternative="greater").statistic
    return float(u / (len(pos) * len(neg)))
