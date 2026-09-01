"""CoSafe — coreference-based multi-turn attacks (ungated), used as the
fragmentation/coreference family. Each category file is JSONL; each line is
a user/assistant message list where the final user turn resolves a
coreference onto harmful intent built up over earlier benign turns.
"""
from __future__ import annotations
import json, glob
from ..schema import Conversation, Turn
from . import base

GLOB = str(base.RAW / "cosafe" / "**" / "*.json")


def load() -> list[Conversation]:
    convs, seen_files = [], 0
    for path in glob.glob(GLOB, recursive=True):
        # skip the single-prompt baseline directory if present
        if "single prompt" in path.lower():
            continue
        category = path.replace("\\", "/").split("/")[-1].replace(".json", "")
        for i, line in enumerate(open(path, encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            try:
                msgs = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(msgs, list):
                continue
            turns = [Turn(m["role"], m["content"]) for m in msgs
                     if m.get("role") in ("user", "assistant") and m.get("content")]
            if sum(t.role == "user" for t in turns) < 2:
                continue
            convs.append(Conversation(
                conv_id=f"cosafe-{category}-{i}",
                source="CoSafe",
                label="attack", family="coreference",
                harm_turn=None,
                category=category,
                turns=turns,
            ))
        seen_files += 1
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"CoSafe: {len(c)} attack conversations, "
          f"avg {sum(x.n_user_turns for x in c)/max(1,len(c)):.1f} user turns")
    base.write_normalized(c, "cosafe_coreference")
    print("wrote data/normalized/cosafe_coreference.jsonl")
