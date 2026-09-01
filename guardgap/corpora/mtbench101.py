"""MT-Bench-101 — BENIGN multi-turn benchmark (ungated). Used as topic-diverse
benign negatives for the false-positive rate. Each row: {task, id, history:[{user,bot}]}.
"""
from __future__ import annotations
import json
from ..schema import Conversation, Turn
from . import base

RAW = base.RAW / "mtbench101" / "data" / "subjective" / "mtbench101.jsonl"


def load(min_user_turns: int = 3) -> list[Conversation]:
    convs = []
    for line in open(RAW, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        turns = []
        for pair in row.get("history", []):
            if pair.get("user"):
                turns.append(Turn("user", pair["user"]))
            if pair.get("bot"):
                turns.append(Turn("assistant", pair["bot"]))
        if sum(t.role == "user" for t in turns) < min_user_turns:
            continue
        convs.append(Conversation(
            conv_id=f"mtb101-{row.get('task')}-{row.get('id')}",
            source="MT-Bench-101",
            label="benign", family=None, harm_turn=None,
            turns=turns,
        ))
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"MT-Bench-101: {len(c)} benign conversations, "
          f"avg {sum(x.n_user_turns for x in c)/max(1,len(c)):.1f} user turns")
    base.write_normalized(c, "mtbench101_benign")
    print("wrote data/normalized/mtbench101_benign.jsonl")
