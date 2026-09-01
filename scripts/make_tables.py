#!/usr/bin/env python
"""Regenerate both result tables from whatever is in the score cache — without
re-running the experiment. Emits Table 2 (commercial) and Table A (local /
reference) plus the configuration-gap decomposition, and writes the CSVs.

    .venv-models\\Scripts\\python.exe scripts\\make_tables.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from guardgap import report  # noqa: E402

if __name__ == "__main__":
    report.two_tier()
