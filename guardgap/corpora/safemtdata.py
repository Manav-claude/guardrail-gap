"""SafeMTData / ActorAttack — DRIFT family (ungated).
Each item's `multi_turn_queries` is the list of attack user turns; the
harmful objective is `plain_query`. We keep the user turns in order; the
final turn is where the payload is solicited, so harm_turn = last turn.
"""
from __future__ import annotations
import json
from ..schema import Conversation, Turn
from . import base

RAW = base.RAW / "safemtdata" / "SafeMTData" / "Attack_600.json"


def load() -> list[Conversation]:
    data = json.load(open(RAW, encoding="utf-8"))
    convs = []
    for item in data:
        queries = item.get("multi_turn_queries") or []
        if len(queries) < 2:
            continue
        turns = [Turn("user", q) for q in queries]
        convs.append(Conversation(
            conv_id=f"safemt-{item.get('id')}",
            source="SafeMTData/Attack_600",
            label="attack", family="drift",
            harm_turn=len(turns),
            category=item.get("category"),
            turns=turns,
        ))
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"SafeMTData: {len(c)} attack conversations, "
          f"avg {sum(x.n_user_turns for x in c)/len(c):.1f} user turns")
    base.write_normalized(c, "safemtdata_drift")
    print("wrote data/normalized/safemtdata_drift.jsonl")
