"""Serialisation + paths shared by all corpus loaders."""
from __future__ import annotations
import json, pathlib
from ..schema import Conversation, Turn

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
NORM = ROOT / "data" / "normalized"


def to_dict(c: Conversation) -> dict:
    return {"conv_id": c.conv_id, "source": c.source, "label": c.label,
            "family": c.family, "harm_turn": c.harm_turn, "category": c.category,
            "turns": [{"role": t.role, "text": t.text} for t in c.turns]}


def from_dict(d: dict) -> Conversation:
    return Conversation(conv_id=d["conv_id"], source=d["source"], label=d["label"],
                        family=d.get("family"), harm_turn=d.get("harm_turn"),
                        category=d.get("category"),
                        turns=[Turn(t["role"], t["text"]) for t in d["turns"]])


def write_normalized(convs: list[Conversation], name: str) -> pathlib.Path:
    NORM.mkdir(parents=True, exist_ok=True)
    out = NORM / f"{name}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for c in convs:
            f.write(json.dumps(to_dict(c), ensure_ascii=False) + "\n")
    return out


def load_normalized(name: str) -> list[Conversation]:
    path = NORM / f"{name}.jsonl"
    return [from_dict(json.loads(l)) for l in open(path, encoding="utf-8")]


def dedup(convs: list[Conversation]) -> list[Conversation]:
    """Drop conversations with an identical concatenation of user turns."""
    seen, out = set(), []
    for c in convs:
        key = "".join(c.user_turns())
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out
