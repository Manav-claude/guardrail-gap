#!/usr/bin/env python
"""Fetch the raw corpora into the exact layout the loaders expect. Nothing is
redistributed by this repository; each source is pulled from its owner under
its own terms (see DATASETS.md), and two sources are gated:

  * ScaleAI/mhj (Hugging Face, gated: accept the terms on the dataset page and
    set HF_TOKEN in .env)
  * marslabucla/XGuard-Train (gated, optional; not used in the paper)

Expected layout after this script:
  data/raw/mhj/                      harmbench_behaviors.csv (+ other CSVs)
  data/raw/safemtdata/SafeMTData/    Attack_600.json
  data/raw/cosafe/                   CoSafe-Dataset repo (pinned commit)
  data/raw/mtbench101/data/subjective/mtbench101.jsonl (pinned commit)
  data/raw/xguardtrain/xguard-train.json   (optional)
WildChat is streamed from the Hub at build time by guardgap/corpora/wildchat.py.

Run:  python scripts/download_datasets.py [--with-xguard]
"""
from __future__ import annotations
import argparse, os, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from guardgap import secrets  # loads .env  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
COSAFE_REPO = "https://github.com/ErxinYu/CoSafe-Dataset"
COSAFE_COMMIT = "a298d9c742203b00eaeca58dfca7100c7e2ff360"
MTB_REPO = "https://github.com/mtbench101/mt-bench-101"
MTB_COMMIT = "bc18b3e2c18c99164e11528f1a79c92083db5953"


def hf_snapshot(repo: str, local: pathlib.Path, allow: list[str] | None = None) -> None:
    from huggingface_hub import snapshot_download
    local.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo, repo_type="dataset", local_dir=str(local),
                      allow_patterns=allow, token=secrets.get("HF_TOKEN"))
    print(f"[ok] {repo} -> {local}")


def git_pinned(url: str, dest: pathlib.Path, commit: str) -> None:
    if not (dest / ".git").exists():
        subprocess.run(["git", "clone", "--quiet", url, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "--quiet", commit], check=True)
    print(f"[ok] {url} @ {commit[:8]} -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-xguard", action="store_true", help="also fetch XGuard-Train (gated, optional)")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if not secrets.get("HF_TOKEN"):
        print("[warn] HF_TOKEN not set: ScaleAI/mhj is gated and will fail; set it in .env after accepting the terms")
    hf_snapshot("ScaleAI/mhj", RAW / "mhj", allow=["*.csv"])
    hf_snapshot("SafeMTData/SafeMTData", RAW / "safemtdata")
    git_pinned(COSAFE_REPO, RAW / "cosafe", COSAFE_COMMIT)
    git_pinned(MTB_REPO, RAW / "mtbench101", MTB_COMMIT)
    if a.with_xguard:
        hf_snapshot("marslabucla/XGuard-Train", RAW / "xguardtrain")
    print("\nnext: python scripts/build_corpora.py")


if __name__ == "__main__":
    main()
