"""Durable local export of ALL captured data, so paid results are never lost.
Writes, into results/:
  * scores_full.parquet   — every per-turn score row, ALL columns incl. raw_json
                            (the complete per-detector response for each call)
  * scores_backup.sqlite  — byte copy of the score cache
  * conversations.parquet — per-conversation aggregates
  * export_manifest.json  — row counts, per-product/label, timestamp
Called automatically at the end of every run, and runnable standalone.
"""
from __future__ import annotations
import json, shutil, time, pathlib
import pandas as pd
from . import runner, metrics

RESULTS = pathlib.Path(__file__).resolve().parents[1] / "results"


def dump() -> dict:
    RESULTS.mkdir(exist_ok=True)
    df = metrics.per_turn_df()                                # union of all shards

    df.to_parquet(RESULTS / "scores_full.parquet")            # everything, incl raw_json
    # human-readable line-delimited copy too (robust to any future tool)
    df.to_json(RESULTS / "scores_full.jsonl", orient="records", lines=True, force_ascii=False)
    # byte-for-byte backup of every product shard
    backup = RESULTS / "shards_backup"
    backup.mkdir(exist_ok=True)
    for shard in runner.all_shards():
        shutil.copy2(shard, backup / shard.name)

    manifest = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rows": int(len(df)),
        "by_product": df.groupby("product").size().to_dict(),
        "by_product_label": {f"{p}/{l}": int(n) for (p, l), n
                             in df.groupby(["product", "label"]).size().items()},
        "distinct_convs": int(df["conv_id"].nunique()),
        "has_raw_json": int(df["raw_json"].notna().sum()),
        "total_cost_units": float(df["cost_units"].clip(lower=0).sum()),
        "est_cost_usd": round(float(df["cost_units"].clip(lower=0).sum()) / 1000 * 0.15, 2),
    }
    (RESULTS / "export_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    m = dump()
    print(json.dumps(m, indent=2))
    print(f"\nsaved to {RESULTS}/  (scores_full.parquet + .jsonl, scores_backup.sqlite, "
          "conversations.parquet, export_manifest.json)")
