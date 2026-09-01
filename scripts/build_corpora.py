#!/usr/bin/env python
"""Normalise every AVAILABLE corpus into data/normalized/*.jsonl and print a
summary. Ungated sets build with no token; gated sets are skipped with a note
unless HF_TOKEN is set. Run in the core venv (has `datasets`).

    python scripts/build_corpora.py
"""
from __future__ import annotations
import sys, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from guardgap.corpora import base, safemtdata, cosafe, mtbench101, wildchat, mhj  # noqa: E402

# (name, loader, gated?)
SOURCES = [
    ("safemtdata_drift",     safemtdata.load, False),
    ("cosafe_coreference",   cosafe.load,     False),
    ("mtbench101_benign",    mtbench101.load, False),
    ("wildchat_benign",      wildchat.load,   False),   # ungated but streams from HF
    ("mhj_escalation",       mhj.load,        True),    # gated: needs HF_TOKEN
]


def main() -> None:
    rows = []
    for name, loader, gated in SOURCES:
        if gated and not os.getenv("HF_TOKEN"):
            print(f"SKIP  {name:24} gated — set HF_TOKEN + accept licence")
            continue
        try:
            convs = loader()
            base.write_normalized(convs, name)
            n = len(convs)
            avg = sum(c.n_user_turns for c in convs) / max(1, n)
            label = convs[0].label if convs else "?"
            fam = convs[0].family if convs else "?"
            rows.append((name, label, fam, n, avg))
            print(f"OK    {name:24} {label:7} {str(fam):12} n={n:<5} avg_user_turns={avg:.1f}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {name:24} {type(e).__name__}: {str(e)[:120]}")

    if rows:
        atk = sum(n for _, l, _, n, _ in rows if l == "attack")
        ben = sum(n for _, l, _, n, _ in rows if l == "benign")
        print(f"\nTotal: {atk} attack + {ben} benign conversations in data/normalized/")


if __name__ == "__main__":
    main()
