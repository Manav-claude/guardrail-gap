#!/usr/bin/env python
"""Run the grid and emit the tables. Products default to whichever are ready
(local always; cloud when creds are present). Results cache in
cache/scores.sqlite (resumable). Tables written to results/.

    # local-only draft (no creds), small sample:
    .venv-models\\Scripts\\python.exe scripts\\run_experiment.py --products local --n 40
    # everything ready, full corpus:
    .venv-models\\Scripts\\python.exe scripts\\run_experiment.py --products ready
"""
from __future__ import annotations
import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from guardgap import runner, metrics, secrets           # noqa: E402
from guardgap.products import registry                  # noqa: E402

CONFIGS = ["last", "full", "m2s"]
ATTACK_CORPORA = ["mhj_escalation", "safemtdata_drift", "cosafe_coreference"]
BENIGN_CORPORA = ["mtbench101_benign", "wildchat_benign"]
RESULTS = pathlib.Path(__file__).resolve().parents[1] / "results"


def pick_products(mode: str) -> list[str]:
    if mode == "local":
        return registry.LOCAL
    if mode == "all":
        return list(registry.REGISTRY)
    if mode in registry.REGISTRY:      # a single product name selects just it
        return [mode]
    # "ready": local + any cloud product whose creds are present
    ready = {p.name for p in secrets.PROVIDERS if p.ready()}
    return registry.LOCAL + [c for c in registry.CLOUD if c in ready]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", default="local", help="local | ready | all | comma list")
    ap.add_argument("--n", type=int, default=None, help="convs sampled per corpus (default all)")
    ap.add_argument("--max-turns", type=int, default=None)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--no-report", action="store_true",
                    help="skip tables+export (use when running products in parallel; "
                         "build once at the end with scripts/make_tables.py + export)")
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
    m = export.dump()   # persist ALL captured data locally (incl. raw per-detector responses)
    print(f"\n[export] {m['rows']} rows saved to results/ (raw_json rows: {m['has_raw_json']}, "
          f"~${m['est_cost_usd']} billed so far)")



if __name__ == "__main__":
    main()
