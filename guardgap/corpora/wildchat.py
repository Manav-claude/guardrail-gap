"""WildChat-1M — BENIGN real user/assistant conversations (ungated). Streamed,
so we never download all ~1M. We sample English, non-toxic, multi-turn
conversations as benign negatives / dilution filler.
"""
from __future__ import annotations
import itertools
from ..schema import Conversation, Turn
from . import base

REPO = "allenai/WildChat-1M"


def load(n: int = 300, min_user_turns: int = 3) -> list[Conversation]:
    from datasets import load_dataset
    ds = load_dataset(REPO, split="train", streaming=True)
    convs = []
    for i, row in enumerate(itertools.islice(ds, 20000)):
        if row.get("toxic") or (row.get("language") not in (None, "English")):
            continue
        msgs = row.get("conversation") or []
        turns = [Turn(m["role"], m["content"]) for m in msgs
                 if m.get("role") in ("user", "assistant") and m.get("content")]
        if sum(t.role == "user" for t in turns) < min_user_turns:
            continue
        convs.append(Conversation(
            conv_id=f"wildchat-{row.get('conversation_hash', i)}",
            source="WildChat-1M",
            label="benign", family=None, harm_turn=None,
            turns=turns,
        ))
        if len(convs) >= n:
            break
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"WildChat sample: {len(c)} benign conversations, "
          f"avg {sum(x.n_user_turns for x in c)/max(1,len(c)):.1f} user turns")
    base.write_normalized(c, "wildchat_benign")
    print("wrote data/normalized/wildchat_benign.jsonl")
