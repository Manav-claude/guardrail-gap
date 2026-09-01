"""Inspection functions I_c (spec §6): map the user-turn prefix to the unit
actually submitted to a detector under configuration c.
"""
from __future__ import annotations

SEP = "\n"   # plain newline; no role tags unless testing that channel


def last(prefix: list[str]) -> str:
    return prefix[-1] if prefix else ""


def full(prefix: list[str]) -> str:
    return SEP.join(prefix)


def window_k(prefix: list[str], k: int) -> str:
    return SEP.join(prefix[-k:])


def m2s(prefix: list[str], template: str = "hyphenize") -> str:
    """Deterministic multi-turn -> single-turn compression (spec §7.2)."""
    if template == "hyphenize":
        return "\n".join("- " + u for u in prefix)
    if template == "numberize":
        return "\n".join(f"{i+1}. {u}" for i, u in enumerate(prefix))
    if template == "pythonize":
        return "prompts = [\n" + ",\n".join(repr(u) for u in prefix) + "\n]"
    raise ValueError(f"unknown m2s template: {template}")


def apply(config: str, prefix: list[str], k: int = 3) -> str:
    if config == "last":
        return last(prefix)
    if config == "full":
        return full(prefix)
    if config == "win-k":
        return window_k(prefix, k)
    if config.startswith("m2s"):
        tmpl = config.split(":", 1)[1] if ":" in config else "hyphenize"
        return m2s(prefix, tmpl)
    raise ValueError(f"unknown config: {config}")
