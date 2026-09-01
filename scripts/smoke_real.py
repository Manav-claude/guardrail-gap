#!/usr/bin/env python
"""Run the free local guards over a small sample of the REAL normalized
corpora, under the three inspection configs, and print detection rates.
This is the actual experiment mechanic on real data (small sample, free
models) — a preview of the paper's Table 2. Run in the models venv:

    .venv-models\\Scripts\\python.exe scripts\\smoke_real.py --n 40
"""
from __future__ import annotations
import sys, pathlib, argparse, random
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from guardgap.corpora import base                          # noqa: E402
from guardgap import policies                              # noqa: E402
from guardgap.products import protectai_deberta, qwen3guard  # noqa: E402

CONFIGS = ["last", "full", "m2s"]
PRODUCTS = {"protectai": protectai_deberta, "qwen3guard": qwen3guard}
CORPORA = ["safemtdata_drift", "cosafe_coreference", "mtbench101_benign"]


def detect(product, users: list[str], config: str) -> int:
    for t in range(1, len(users) + 1):
        if product.score(policies.apply(config, users[:t])).blocked:
            return 1
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="conversations sampled per corpus")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    print(f"{'product':11} {'corpus':22} {'label':7} n  "
          + "  ".join(f"{c:>6}" for c in CONFIGS) + "   (detection rate)")
    print("-" * 74)
    for pname, prod in PRODUCTS.items():
        for corpus in CORPORA:
            convs = base.load_normalized(corpus)
            rng.shuffle(convs)
            convs = convs[:args.n]
            label = convs[0].label
            rates = []
            for c in CONFIGS:
                d = sum(detect(prod, cv.user_turns(), c) for cv in convs) / len(convs)
                rates.append(d)
            print(f"{pname:11} {corpus:22} {label:7} {len(convs):<3}"
                  + "  ".join(f"{r:6.2f}" for r in rates))
    print("\nAttack corpora: higher is better (caught). Benign: this IS the false-"
          "positive rate, lower is better. A jump from 'last' to 'full'/'m2s' on an "
          "attack row = the configuration gap. Small free-model sample; the paper "
          "runs the full grid across the five commercial guardrails.")


if __name__ == "__main__":
    main()
