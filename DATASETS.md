# Datasets

GuardGap does **not** redistribute any evaluation data. The corpora are
third-party, carry their own licences, and several contain harmful text. To
replicate, obtain them yourself from the sources below (a script does the
fetching) and let the loaders normalise them into the common schema.

```
python scripts/download_datasets.py        # fetches everything below into data/raw/
python scripts/build_corpora.py            # normalises into data/normalized/*.jsonl
```

Both directories are git-ignored.

## Expected raw layout (what the loaders hard-code)

| Path | Source | Pinned |
|---|---|---|
| `data/raw/mhj/*.csv` (`harmbench_behaviors.csv` ...) | Hugging Face `ScaleAI/mhj` | latest |
| `data/raw/safemtdata/SafeMTData/Attack_600.json` | Hugging Face `SafeMTData/SafeMTData` | latest |
| `data/raw/cosafe/` (repo checkout) | GitHub `ErxinYu/CoSafe-Dataset` | commit `a298d9c7` |
| `data/raw/mtbench101/data/subjective/mtbench101.jsonl` | GitHub `mtbench101/mt-bench-101` | commit `bc18b3e2` |
| `data/raw/xguardtrain/xguard-train.json` (optional) | Hugging Face `marslabucla/XGuard-Train` | latest |

WildChat is streamed from the Hub at build time (`guardgap/corpora/wildchat.py`).

## Attack corpora (three families)

| Family (paper) | Code name | Dataset | Access / licence |
|---|---|---|---|
| Escalation | `escalation` | MHJ - Multi-turn Human Jailbreaks (`ScaleAI/mhj`) | Gated (auto-accept after agreeing to terms); CC-BY-NC-4.0 |
| Drift | `drift` | SafeMTData / ActorAttack `Attack_600` | Ungated; MIT |
| Coreference | `coreference` | CoSafe (EMNLP 2024) | No licence file in the GitHub repo; used for research per the paper - confirm terms with the authors |

The paper calls the third family **coreference** (a harmful antecedent introduced
early and referenced pronominally later). It is not a decomposition/fragmentation
corpus in the sense of individually benign sub-requests.

Optional, excluded from the labelled attack set by default: XGuard-Train
(gated, auto-accept; no licence declared) - a safety-training mix without
per-conversation harm labels; loader `guardgap/corpora/xguard.py`.

Corpus sizes used in the paper: 489 escalation, 600 drift, 1400 coreference
(2489 attacks); 927 MT-Bench-101 + 300 WildChat (1227 benign).

## Benign corpora (for false-positive rate)

| Dataset | Source | Licence | Notes |
|---|---|---|---|
| MT-Bench-101 | GitHub `mtbench101/mt-bench-101` | Apache-2.0 | multi-turn benchmark; loader `guardgap/corpora/mtbench101.py` |
| WildChat-1M | Hugging Face `allenai/WildChat-1M` | ODC-BY (ungated) | streamed sample; loader keeps English, non-toxic, multi-turn |

## Guard models (reference tier, run locally)

| Model | Hugging Face id | Access / licence |
|---|---|---|
| Prompt Guard 2 (86M) | `meta-llama/Llama-Prompt-Guard-2-86M` | Gated (manual approval); Llama 4 Community Licence |
| ProtectAI DeBERTa v2 | `protectai/deberta-v3-base-prompt-injection-v2` | Apache-2.0, ungated |
| Qwen3Guard-Gen-0.6B | `Qwen/Qwen3Guard-Gen-0.6B` | Apache-2.0, ungated |

## Hugging Face access

Gated items need a Hugging Face token in `.env` (`HF_TOKEN=...`) and acceptance
of each page's terms while logged in to that account. See `.env.example`.

## Reproducibility note

Loaders assign a stable `conv_id` per conversation and preserve each item's
harm category, so the published aggregate results (`results_public/`) reference
conversations by id and rate only, never by text.
