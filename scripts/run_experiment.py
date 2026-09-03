#!/usr/bin/env python
"""Run the grid (products x inspection configurations x corpora) and, unless
--no-report is given, emit the tables. Per-call results are cached in
cache/scores_<product>.sqlite (resumable); tables are written to results/.

    # quick draft on the open models (models env), 40 conversations per corpus:
    python scripts/run_experiment.py --products local --n 40
    # one commercial product, full corpus, tables built later:
    python scripts/run_experiment.py --products bedrock --no-report
    # everything whose credentials (and torch, for local models) are present:
    python scripts/run_experiment.py --products ready
"""
from __future__ import annotations
import sys, pathlib, argparse, importlib.util
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from guardgap import runner, metrics, secrets           # noqa: E402
from guardgap.products import registry                  # noqa: E402

CONFIGS = ["last", "full", "m2s"]
ATTACK_CORPORA = ["mhj_escalation", "safemtdata_drift", "cosafe_coreference"]
BENIGN_CORPORA = ["mtbench101_benign", "wildchat_benign"]
RESULTS = pathlib.Path(__file__).resolve().parents[1] / "results"


def pick_products(mode: str) -> list[str]:
    if mode == "local":
        return list(registry.LOCAL)
    if mode == "all":
        return list(registry.LOCAL) + list(registry.CLOUD)
    if mode in registry.REGISTRY:      # a single product name selects just it
        return [mode]
    if mode != "ready":
        sys.exit(f"unknown --products value '{mode}' (local | ready | all | name | comma list)")
    # "ready": local models only if torch is importable (and HF_TOKEN for the
    # gated Prompt Guard 2); cloud products whose credentials are present.
    torch_ok = importlib.util.find_spec("torch") is not None
    local = [p for p in registry.LOCAL
             if torch_ok and (p != "prompt_guard2" or secrets.get("HF_TOKEN"))]
    ready = {p.name for p in secrets.PROVIDERS if p.ready()}
    return local + [c for c in registry.CLOUD if c in ready]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", default="local", help="local | ready | all | name | comma list")
    ap.add_argument("--n", type=int, default=None, help="conversations sampled per corpus (default all)")
    ap.add_argument("--max-turns", type=int, default=None)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--no-report", action="store_true",
                    help="skip tables+export (use when running products in parallel; "
                         "build once at the end with scripts/make_tables.py)")
    args = ap.parse_args()

    products = (args.products.split(",") if "," in args.products
                else pick_products(args.products))
    configs = args.configs.split(",")
    corpora = ATTACK_CORPORA + BENIGN_CORPORA
    print(f"products: {products}\nconfigs:  {configs}\ncorpora:  {corpora}\n"
          f"sample:   {args.n or 'ALL'} per corpus\n")

    stats = runner.run(products, configs, corpora, n=args.n, max_turns=args.max_turns)
    print(f"\nrunner: +{stats['new_calls']} new calls, {stats['cached']} cached\n")

    if args.no_report:
        print("[--no-report] skipping tables/export; run scripts/make_tables.py after all runs")
        return

    from guardgap import report, export
    conv = metrics.conversation_table()
    RESULTS.mkdir(exist_ok=True)
    conv.to_parquet(RESULTS / "conversations.parquet")
    report.two_tier(conv, configs)
    m = export.dump()   # persist all captured data locally (incl. raw per-detector responses)
    print(f"\n[export] {m['rows']} rows saved to results/ (raw_json rows: {m['has_raw_json']})")


if __name__ == "__main__":
    main()
