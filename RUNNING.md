# Reproducing the paper's runs

This is the exact sequence used for *What the Guardrail Sees*. Every step is
resumable: per-call results are cached in `cache/scores_<product>.sqlite` and
re-running only computes what is missing.

## 1. Two Python environments (why two)

The cloud SDKs run on any current Python; PyTorch does not ship wheels for the
newest interpreters. So:

- **core** (cloud guardrails, data, statistics): `python -m venv .venv`, activate,
  `pip install -r requirements-core.txt`.
- **models** (the three open guard models; Python 3.11-3.13 with torch):
  `python -m venv .venv-models`, activate, `pip install -r requirements-local-models.txt`.
  The models env is a superset, so every script also runs from it.

## 2. Secrets and provisioning

1. `cp .env.example .env` and fill in what you have. Blank providers are SKIPped.
2. Provision the detect-mode resources used in the paper:
   - AWS: `python infra/aws_provision_guardrail.py` - six content filters at HIGH,
     the eight denied-topic definitions, every action NONE; prints the id/version
     to paste into `.env`.
   - Azure: `bash infra/azure_provision.sh` (or create a Content Safety resource in
     the portal); one endpoint + key serves both Prompt Shields and text analysis.
     The paper used the S0 tier (the F0 free tier's quota is exhausted mid-run).
   - GCP: `bash infra/gcp_provision.sh` - a Model Armor template with every filter
     at LOW_AND_ABOVE; set `MODEL_ARMOR_TEMPLATE_ID`.
   - Meta Prompt Guard 2 is gated: accept the licence on its model page, set
     `HF_TOKEN`, then `python infra/local_models_download.py` (models env).
3. `python scripts/check_creds.py` - every configured provider should print OK.

## 3. Data

```
python scripts/download_datasets.py     # MHJ (gated), SafeMTData, CoSafe, MT-Bench-101; WildChat streams
python scripts/build_corpora.py         # -> data/normalized/*.jsonl
```

Expected: 489 `mhj_escalation`, 600 `safemtdata_drift`, 1400 `cosafe_coreference`
(attacks); 927 `mtbench101_benign`, 300 `wildchat_benign`. `xguard_mixed` (300,
unlabelled) is built if present but never used in the tables.

## 4. Runs (one product per process; they share nothing but the corpora)

```
# core env
python scripts/run_experiment.py --products bedrock              --no-report
python scripts/run_experiment.py --products azure_prompt_shields --no-report
python scripts/run_experiment.py --products azure_text           --no-report
python scripts/run_experiment.py --products model_armor          --no-report
# models env
python scripts/run_experiment.py --products protectai_deberta    --no-report
python scripts/run_experiment.py --products qwen3guard           --no-report
python scripts/run_experiment.py --products prompt_guard2        --no-report
```

Each run scores every conversation under the three inspection configurations
(`last`, `full`, `m2s`) and persists the raw per-detector response of every
call. Products may run concurrently (separate shards). `--n 40` gives a quick
draft; omit it for the full corpus.

## 5. Tables and public results

```
python scripts/make_tables.py            # console Table 2 / Table A / per-detector tables -> results/
python scripts/make_public_results.py    # results_public/: CIs, strength curve, per-decision, evasion, ...
python scripts/eval_cusum.py             # results_public/cusum_matched_budget.csv
```

`results/` holds the full local export (including raw responses) and is
git-ignored; `results_public/` holds only aggregates and is committed.

## 6. Cost and safety

- Bedrock billed about 114k text units (~USD 17) for the full grid; Azure S0
  about 55k records per API; Model Armor stayed inside its free tier.
- Set a billing alert before full runs. `.env`, keys, model weights, raw data
  and `results/` are git-ignored; never commit credentials.
