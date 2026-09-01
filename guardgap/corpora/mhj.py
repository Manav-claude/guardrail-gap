"""MHJ (Scale AI) — ESCALATION family. GATED: needs HF_TOKEN in .env AND the
account to have accepted the gate at https://huggingface.co/datasets/ScaleAI/mhj
(gated=auto -> instant on click). Pull with scripts/build_corpora.py, which
snapshot-downloads harmbench_behaviors.csv into data/raw/mhj/.

Schema (verified 2026-08-29): one row per human multi-turn jailbreak; columns
Source, tactic, question_id, submission_message, and message_0..message_100,
each a JSON string {"body": str, "role": user|assistant|system} or "nan".
"""
from __future__ import annotations
import os, json, math, pathlib
from ..schema import Conversation, Turn
from . import base

CSV = base.RAW / "mhj" / "harmbench_behaviors.csv"


def _download_if_needed() -> None:
    if CSV.exists():
        return
    tok = os.getenv("HF_TOKEN")
    if not tok:
        raise RuntimeError("MHJ is gated: set HF_TOKEN in .env and accept the gate "
                           "at https://huggingface.co/datasets/ScaleAI/mhj , then re-run.")
    from huggingface_hub import snapshot_download
    snapshot_download("ScaleAI/mhj", repo_type="dataset",
                      local_dir=str(base.RAW / "mhj"), token=tok,
                      allow_patterns=["*.csv"])


def _parse_message(cell) -> Turn | None:
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return None
    s = str(cell).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        obj = json.loads(s)
        role, body = obj.get("role", "user"), obj.get("body", "")
    except json.JSONDecodeError:
        role, body = "user", s
    if not body:
        return None
    return Turn(role, body)


def load(n: int | None = None) -> list[Conversation]:
    _download_if_needed()
    import pandas as pd
    df = pd.read_csv(CSV)
    msg_cols = [c for c in df.columns if c.startswith("message_")]
    msg_cols.sort(key=lambda c: int(c.split("_")[1]))
    convs = []
    for i, row in df.iterrows():
        turns = [t for t in (_parse_message(row[c]) for c in msg_cols) if t]
        turns = [t for t in turns if t.role in ("user", "assistant")]  # drop system
        if sum(t.role == "user" for t in turns) < 2:
            continue
        convs.append(Conversation(
            conv_id=f"mhj-{row.get('question_id', i)}-{i}",
            source="ScaleAI/mhj", label="attack", family="escalation",
            harm_turn=None, category=str(row.get("tactic")), turns=turns))
        if n and len(convs) >= n:
            break
    return base.dedup(convs)


if __name__ == "__main__":
    c = load()
    print(f"MHJ: {len(c)} attack conversations, "
          f"avg {sum(x.n_user_turns for x in c)/max(1,len(c)):.1f} user turns")
    base.write_normalized(c, "mhj_escalation")
    print("wrote data/normalized/mhj_escalation.jsonl")
