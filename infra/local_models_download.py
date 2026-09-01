#!/usr/bin/env python
"""Pre-download the local guard model weights (Prompt Guard 2) so the
first experiment run is offline and fast.

Gated Meta model: you must (1) put HF_TOKEN in .env and (2) accept the
licence at https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
while logged into that HF account.

Run inside the MODELS venv (torch present):
    python infra/local_models_download.py
"""
from __future__ import annotations
import os, sys, pathlib
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MODELS = ["meta-llama/Llama-Prompt-Guard-2-86M"]  # add -22M or Llama-Guard-4 here if wanted
CACHE = ROOT / "models"

def main() -> None:
    tok = os.getenv("HF_TOKEN")
    if not tok:
        sys.exit("HF_TOKEN not set in .env")
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit("run inside the models venv: pip install -r requirements-local-models.txt")

    for repo in MODELS:
        print(f"downloading {repo} ...")
        path = snapshot_download(repo_id=repo, token=tok, cache_dir=str(CACHE))
        print(f"  -> {path}")
    print("done. Prompt Guard 2 is cached under ./models")

if __name__ == "__main__":
    main()
