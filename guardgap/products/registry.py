"""Product registry — maps a product name to its score() callable, imported
lazily so cloud SDKs / torch load only when that product is actually used.

Every product module exposes:  score(unit: str, source: str="INPUT") -> Score
and a module-level  VERSION: str  (for cache keys and drift tracking).
"""
from __future__ import annotations
import importlib
from ..schema import Score

# name -> (module, kind). kind: "local" (torch, open reference tier), "cloud"
# (commercial API evaluated in the paper), or "experimental" (present but not
# evaluated; excluded from `--products local/ready/all`, selectable by name).
REGISTRY = {
    # open reference tier (torch)
    "protectai_deberta": ("guardgap.products.protectai_deberta", "local"),
    "qwen3guard":        ("guardgap.products.qwen3guard", "local"),
    "prompt_guard2":     ("guardgap.products.prompt_guard2", "local"),
    # commercial cloud products evaluated in the paper (need creds in .env)
    "bedrock":              ("guardgap.products.bedrock", "cloud"),
    "azure_prompt_shields": ("guardgap.products.azure_prompt_shields", "cloud"),
    "azure_text":           ("guardgap.products.azure_text", "cloud"),
    "model_armor":          ("guardgap.products.model_armor", "cloud"),
    # hosted Llama Guard adapter: provided, not evaluated in the paper
    "llama_guard4":         ("guardgap.products.llama_guard4", "experimental"),
}

LOCAL = [n for n, (_, k) in REGISTRY.items() if k == "local"]
CLOUD = [n for n, (_, k) in REGISTRY.items() if k == "cloud"]

_CACHE: dict[str, object] = {}


def get(name: str):
    """Return the product module (lazily imported)."""
    if name not in REGISTRY:
        raise KeyError(f"unknown product '{name}'. known: {list(REGISTRY)}")
    if name not in _CACHE:
        _CACHE[name] = importlib.import_module(REGISTRY[name][0])
    return _CACHE[name]


def version(name: str) -> str:
    return getattr(get(name), "VERSION", "unknown")


def score(name: str, unit: str, source: str = "INPUT") -> Score:
    return get(name).score(unit, source)
