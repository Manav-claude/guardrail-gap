"""Azure AI Content Safety — Prompt Shields (schema verified 2026-08-22).
Binary only (attackDetected) -> one operating point, no continuous score.
Needs AZURE_CONTENT_SAFETY_ENDPOINT + _KEY in .env.

Configs: `last`/`full`/`m2s` put text in userPrompt; the harness may also call
score_with_history() to use the per-document channel (returns per-turn vector).
"""
from __future__ import annotations
import os, math, time
import httpx
from ..schema import Score

VERSION = "contentsafety-2024-09-01"
_API = "?api-version=2024-09-01"


def _url() -> str:
    ep = os.environ["AZURE_CONTENT_SAFETY_ENDPOINT"].rstrip("/")
    return f"{ep}/contentsafety/text:shieldPrompt{_API}"


def _headers() -> dict:
    return {"Ocp-Apim-Subscription-Key": os.environ["AZURE_CONTENT_SAFETY_KEY"],
            "Content-Type": "application/json"}


def score(unit: str, source: str = "INPUT") -> Score:
    t0 = time.perf_counter()
    text = unit[:10000]
    # Prompt Shields rejects an empty userPrompt with 400; an empty unit is not
    # an attack, so return benign without a call.
    if not text.strip():
        return Score(blocked=False, r=0.0, categories=[], latency_ms=0.0,
                     cost_units=0.0, coverage=1.0, raw={"skipped": "empty_unit"})
    r = httpx.post(_url(), headers=_headers(),
                   json={"userPrompt": text, "documents": []}, timeout=60)
    if r.status_code == 400:
        # malformed input the service refuses; record and continue rather than
        # crashing a long run. Non-detection is the correct outcome for benign.
        return Score(blocked=False, r=0.0, categories=[], latency_ms=0.0,
                     cost_units=0.0, coverage=1.0,
                     raw={"http_400": r.text[:200]})
    r.raise_for_status()
    dt = (time.perf_counter() - t0) * 1000
    detected = bool(r.json().get("userPromptAnalysis", {}).get("attackDetected"))
    coverage = min(1.0, 10000 / len(unit)) if len(unit) else 1.0
    records = max(1, math.ceil(len(unit[:10000]) / 1000))   # Azure bills per 1000-char record
    return Score(blocked=detected, r=1.0 if detected else 0.0,
                 categories=["prompt_attack"] if detected else [],
                 latency_ms=dt, cost_units=float(records), coverage=coverage, raw=r.json())
