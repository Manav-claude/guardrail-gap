"""Azure AI Content Safety — Analyze Text. Severity per category at the FINEST
granularity (EightSeverityLevels, 0-7) for Hate / SelfHarm / Sexual / Violence.
The API returns severity regardless of any threshold, so one call captures the
full gradient — reconstruct any action threshold post-hoc. Full per-category
detail is persisted in Score.raw.
"""
from __future__ import annotations
import os, math, time
import httpx
from ..schema import Score

VERSION = "contentsafety-analyze-8level-2024-09-01"
_API = "?api-version=2024-09-01"
_MAXSEV = 7                       # EightSeverityLevels -> 0..7
NOMINAL_BLOCK = 2                 # nominal action level; real threshold reconstructable from raw


def _url() -> str:
    ep = os.environ["AZURE_CONTENT_SAFETY_ENDPOINT"].rstrip("/")
    return f"{ep}/contentsafety/text:analyze{_API}"


def score(unit: str, source: str = "INPUT") -> Score:
    t0 = time.perf_counter()
    r = httpx.post(_url(),
                   headers={"Ocp-Apim-Subscription-Key": os.environ["AZURE_CONTENT_SAFETY_KEY"],
                            "Content-Type": "application/json"},
                   json={"text": unit[:10000], "outputType": "EightSeverityLevels"}, timeout=60)
    r.raise_for_status()
    dt = (time.perf_counter() - t0) * 1000
    body = r.json()
    cats = body.get("categoriesAnalysis", [])
    sev = max((c.get("severity", 0) for c in cats), default=0)
    hits = [c["category"] for c in cats if c.get("severity", 0) >= NOMINAL_BLOCK]
    records = max(1, math.ceil(len(unit[:10000]) / 1000))   # Azure bills per 1000-char record
    return Score(blocked=sev >= NOMINAL_BLOCK, r=sev / _MAXSEV,
                 categories=hits, latency_ms=dt, cost_units=float(records),
                 coverage=min(1.0, 10000 / len(unit)) if len(unit) else 1.0,
                 raw=body)   # full per-category severities kept
