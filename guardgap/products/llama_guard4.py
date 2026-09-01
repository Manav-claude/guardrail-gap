"""Meta Llama Guard 4 — hosted via OpenRouter / Together / Groq (the 12B is
impractical on CPU). Needs LLAMA_GUARD_API_KEY / _MODEL / _PROVIDER in .env.
Llama Guard replies 'safe' or 'unsafe\\n<categories>'.
"""
from __future__ import annotations
import os, time
import httpx
from ..schema import Score

VERSION = "llama-guard-4-hosted"
_BASE = {"openrouter": "https://openrouter.ai/api/v1",
         "together": "https://api.together.xyz/v1",
         "groq": "https://api.groq.com/openai/v1"}


def _endpoint() -> str:
    prov = os.getenv("LLAMA_GUARD_PROVIDER", "openrouter")
    return f"{_BASE[prov]}/chat/completions"


def score(unit: str, source: str = "INPUT") -> Score:
    t0 = time.perf_counter()
    role = "assistant" if source == "OUTPUT" else "user"
    r = httpx.post(_endpoint(),
                   headers={"Authorization": f"Bearer {os.environ['LLAMA_GUARD_API_KEY']}"},
                   json={"model": os.environ["LLAMA_GUARD_MODEL"],
                         "messages": [{"role": role, "content": unit}],
                         "max_tokens": 32, "temperature": 0.0},
                   timeout=90)
    r.raise_for_status()
    dt = (time.perf_counter() - t0) * 1000
    out = r.json()
    text = out["choices"][0]["message"]["content"].strip().lower()
    unsafe = text.startswith("unsafe")
    cats = [c.strip() for c in text.splitlines()[1:]] if unsafe else []
    usage = out.get("usage", {})
    return Score(blocked=unsafe, r=1.0 if unsafe else 0.0, categories=cats,
                 latency_ms=dt, cost_units=float(usage.get("total_tokens", 0)),
                 coverage=1.0, raw={"verdict": text[:60]})
