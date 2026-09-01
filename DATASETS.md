# Datasets

GuardGap does **not** redistribute any evaluation data. The corpora are
third-party, carry their own licences, and several contain harmful text. To
replicate, obtain them yourself from the sources below and let the loaders
normalise them into the common schema.

Place raw downloads under `data/raw/` (git-ignored). Then run:

```
python scripts/build_corpora.py
```

which writes normalised conversations to `data/normalized/*.jsonl` (also
git-ignored) and prints a summary.

## Attack corpora (three families)

| Family | Dataset | Source | Licence / access |
|---|---|---|---|
| Escalation | MHJ (Multi-turn Human Jailbreaks) | Hugging Face `ScaleAI/mhj` | Gated; accept terms on the dataset page. CC-BY-NC. Loader: `guardgap/corpora/mhj.py` |
| Drift | SafeMTData (ActorAttack) | Hugging Face `SafeMTData/SafeMTData` (`Attack_600.json`) | Open; research use. Loader: `guardgap/corpora/safemtdata.py` |
| Fragmentation | CoSafe | GitHub `ErxinYu/CoSafe-Dataset` | See repo licence. Loader: `guardgap/corpora/cosafe.py` |

Optional additional attack source (mixed/unlabeled; excluded from the labelled
attack set by default): XGuard-Train, Hugging Face `marslabucla/XGuard-Train`
(gated) — loader `guardgap/corpora/xguard.py`.

## Benign corpora (for false-positive rate)

| Dataset | Source | Notes |
|---|---|---|
| MT-Bench-101 | GitHub `mtbench101/mt-bench-101` | Multi-turn benchmark; loader `guardgap/corpora/mtbench101.py` |
| WildChat-1M | Hugging Face `allenai/WildChat-1M` | Streamed sample; loader filters to English, non-toxic, multi-turn |

## Hugging Face access

Gated datasets and the open guard models need a Hugging Face token in `.env`
(`HF_TOKEN=...`) and, for gated items, acceptance of each page's terms while
logged in to that account. See `.env.example`.

## Reproducibility note

Loaders assign a stable `conv_id` per conversation and preserve each item's
harm category, so published aggregate results (detection rates, per-detector
tables) reference conversations by id without exposing their text.
