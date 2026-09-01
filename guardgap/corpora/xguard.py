"""XGuard-Train (marslabucla) — multi-turn dialogues from X-Teaming. GATED
(accept at https://huggingface.co/datasets/marslabucla/XGuard-Train).

CAVEAT: this is a safety-TRAINING mix — it interleaves adversarial and benign
multi-turn conversations and this file carries NO per-conversation harm label
(schema is just conversations:[{from:human|gpt,value}]). So it cannot be used
as a clean attack corpus without labels. We therefore expose it only as an
optional, explicitly-labelled 'unlabeled_mixed' source, sampled, and DO NOT
include it in the default attack set (build_corpora leaves it out). Use MHJ /
SafeMTData / CoSafe for labelled attacks.
"""
from __future__ import annotations
import os, json, itertools
from ..schema import Conversation, Turn
from . import base

JSON = base.RAW / "xguardtrain" / "xguard-train.json"
_FROM = {"human": "user", "gpt": "assistant", "user": "user", "assistant": "assistant"}


def load(n: int = 300) -> list[Conversation]:
    if not JSON.exists():
        raise RuntimeError("XGuard not downloaded: accept the gate at "
                           "https://huggingface.co/datasets/marslabucla/XGuard-Train "
                           "then run scripts/download_datasets.py")
    # 673 MB file — stream items with ijson if available, else json.load
    try:
        import ijson
        src = ijson.items(open(JSON, "rb"), "item")
    except ImportError:
        src = iter(json.load(open(JSON, encoding="utf-8")))
    convs = []
    for i, item in enumerate(itertools.islice(src, n * 4)):
        turns = [Turn(_FROM.get(m.get("from"), "user"), m.get("value", ""))
                 for m in item.get("conversations", []) if m.get("value")]
        if sum(t.role == "user" for t in turns) < 2:
            continue
        convs.append(Conversation(
            conv_id=f"xguard-{i}", source="XGuard-Train",
            label="unlabeled_mixed", family="xteaming_mixed",
            harm_turn=None, turns=turns))
        if len(convs) >= n:
            break
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"XGuard sample: {len(c)} conversations (UNLABELED mix), "
          f"avg {sum(x.n_user_turns for x in c)/max(1,len(c)):.1f} user turns")
    base.write_normalized(c, "xguard_mixed")
    print("wrote data/normalized/xguard_mixed.jsonl")
