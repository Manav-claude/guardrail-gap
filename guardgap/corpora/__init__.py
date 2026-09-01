"""Dataset loaders. Each normalises a raw corpus into guardgap.schema.Conversation
and writes data/normalized/<name>.jsonl via base.write_normalized.

Ungated (download + load with no token): safemtdata, cosafe, mtbench101, wildchat.
Gated (need HF_TOKEN + accepted licence): mhj, xguard.
"""
