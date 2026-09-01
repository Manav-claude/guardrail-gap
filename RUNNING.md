# GuardGap — experiment infrastructure

The measurement harness for *What the Guardrail Sees* (see
`../research/05-paper-build-spec.md` for the full design and
`../project_context.md` for project state).

## What the assistant could and could not stand up

**Cannot** (gated behind your billing / identity / MFA — no key was invented):
AWS / Azure / GCP accounts and their keys, the Hugging Face account + licence
acceptance, and the hosted Llama Guard key. You create those; the scripts below
turn them into working infrastructure.

**Stood up for you (real):** the Python environment, the package skeleton, the
provisioning scripts, the `.env` scaffold, and the credential preflight.

## Free / no-credential path (works right now)

Two **ungated** guard models are wired in and verified — no token, no licence,
zero cost. They run in the models venv (already built with Python 3.13 + torch
2.13 CPU):

- `guardgap/products/protectai_deberta.py` — ProtectAI DeBERTa v2 prompt-injection
  detector (the detector inside the ProtectAI/LLM Guard product). Continuous score,
  ~70 ms CPU.
- `guardgap/products/qwen3guard.py` — Qwen3Guard-Gen-0.6B, a current conversational
  guard model; the open stand-in for Llama Guard until you add your HF token.

Verify / demo (models venv):
```powershell
.\.venv-models\Scripts\python.exe -m guardgap.products.protectai_deberta
.\.venv-models\Scripts\python.exe -m guardgap.products.qwen3guard
.\.venv-models\Scripts\python.exe scripts\smoke_local.py   # config-gap mechanic, free
```
`check_creds.py` run from the models venv reports these two as **OK** and the
credentialed providers as SKIP. Models are cached under `./models` (git-ignored).

**Why these and not Llama Guard / Prompt Guard 2:** both Meta models are
`gated=manual` on Hugging Face — they need your logged-in account and accepted
licence, which cannot be done for you. Add `HF_TOKEN` to `.env`, accept the
licence on each model page, then `python infra/local_models_download.py`.

## Datasets (status as of 2026-08-29)

Downloaded, normalised into `data/normalized/*.jsonl` (schema:
`guardgap.schema.Conversation`), and validated:

| Corpus | Family | Label | Convs | Avg user turns | Source |
|---|---|---|---|---|---|
| `mhj_escalation`     | escalation   | attack | 489  | 5.8 | ScaleAI/mhj (HF, gated — accepted) |
| `safemtdata_drift`   | drift        | attack | 600  | 5.0 | SafeMTData/Attack_600 (HF, ungated) |
| `cosafe_coreference` | coreference  | attack | 1400 | 3.0 | CoSafe (GitHub) |
| `mtbench101_benign`  | –            | benign | 927  | 3.5 | MT-Bench-101 (GitHub) |
| `wildchat_benign`    | –            | benign | 300  | 5.6 | WildChat-1M (HF, ungated, streamed sample) |
| `xguard_mixed`       | xteaming_mixed | **unlabeled** | 300 | 7.0 | XGuard-Train (HF, gated — accepted) |

**Total: 2489 labelled attack + 1227 benign** (three attack families), plus 300 unlabeled
XGuard. Rebuild any time: `python scripts/build_corpora.py` (core venv). Raw downloads live
in `data/raw/` (git-ignored, ~675 MB).

> **XGuard caveat:** XGuard-Train is a safety-training *mix* (attack + benign) with no
> per-conversation harm label in the file, so it is stored as `label=unlabeled_mixed` and
> is **excluded from the attack set**. Use MHJ / SafeMTData / CoSafe for labelled attacks.

Meta gated **models** on this account ARE accepted: Prompt Guard 2 is downloaded and
working; Llama Guard 4 (12B, ~24 GB) is accessible but intentionally not downloaded —
run it via a hosted API (`LLAMA_GUARD_*` in `.env`), not local CPU.

Local guards working now (models venv): ProtectAI DeBERTa, Qwen3Guard-0.6B (both free/
ungated), and Prompt Guard 2 (Meta, gated, downloaded). Preview the mechanic on real
data: `.venv-models\Scripts\python.exe scripts\smoke_real.py --n 40`.

## Order of operations

1. **Fill secrets.** `copy .env.example .env` and work through it top to bottom —
   every value has a "where to get it" note. You do not need all providers at
   once; the preflight SKIPs blank ones.

2. **Provision the cloud resources** (each writes the IDs you paste back into `.env`):
   - AWS Bedrock guardrail — `python infra/aws_provision_guardrail.py`
     (pure boto3, no AWS CLI needed; needs AWS keys in `.env` first).
   - Azure Content Safety — `bash infra/azure_provision.sh` (needs Azure CLI)
     or create it in the portal and copy endpoint + key.
   - GCP Model Armor — `bash infra/gcp_provision.sh` (needs gcloud + ADC login).

3. **Local model** (optional for MVP, needed for Prompt Guard 2 results):
   see "Two Python environments" below, then
   `python infra/local_models_download.py`.

4. **Preflight.** `python scripts/check_creds.py` — hits each configured
   provider's cheapest endpoint and prints OK / FAIL / SKIP. Green (or SKIP)
   across the board = ready to run experiments.

## Two Python environments (why)

This machine has **Python 3.14**, which the cloud SDKs support but **PyTorch does
not yet ship wheels for**. So:

- **Core venv (3.14, here):** cloud guardrails + data + stats.
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install -r requirements-core.txt
  ```
- **Models venv (3.11/3.12):** only for local Prompt Guard 2 / Llama Guard.
  ```powershell
  py -3.12 -m venv .venv-models
  .\.venv-models\Scripts\Activate.ps1
  python -m pip install -r requirements-local-models.txt
  ```
  No 3.12 installed? Either `winget install Python.Python.3.12`, or skip local
  models and run Llama Guard via a hosted API (`LLAMA_GUARD_*` in `.env`).

## Layout

```
experiment/
├── .env.example / .env         secrets (only .example is committed)
├── requirements-core.txt       cloud + data (py3.14 OK)
├── requirements-local-models.txt  torch + transformers (py3.11/3.12)
├── infra/
│   ├── aws_provision_guardrail.py   boto3 -> Bedrock guardrail (prints id/version)
│   ├── azure_provision.sh           az CLI -> Content Safety (prints endpoint/key)
│   ├── gcp_provision.sh             gcloud -> Model Armor template (prints ids)
│   └── local_models_download.py     HF -> Prompt Guard 2 weights
├── scripts/
│   └── check_creds.py          preflight: OK / FAIL / SKIP per provider
└── guardgap/
    ├── secrets.py              .env loader + per-provider readiness
    ├── schema.py               Conversation / Turn / Score
    ├── policies.py             inspection functions (last/full/win-k/m2s)
    └── products/prompt_guard2.py   first product (free, local, runnable)
```

## Running the experiment (engine is built)

```powershell
# local-only draft (no cloud creds), small sample:
.\.venv-models\Scripts\python.exe scripts\run_experiment.py --products local --n 40
# once cloud creds are in .env (check_creds shows OK), the real run:
.\.venv-models\Scripts\python.exe scripts\run_experiment.py --products ready
```
- `--products` = `local` | `ready` (local + any cloud product with creds) | `all` | a comma list.
- `--n` samples that many conversations per corpus (omit = full corpus); `--max-turns` caps turns.
- Every call is cached in `cache/scores.sqlite`, so runs are **resumable** and re-runs are free;
  adding a product or raising `--n` only computes what's new.
- Outputs: `results/table2_cdr.csv`, `results/conversations.parquet`, and a printed
  Table 2 + configuration-gap decomposition (GMG, McNemar p, config- vs model-induced, AUROC).

Engine modules (`guardgap/`): `products/registry.py` + per-product adapters, `runner.py`
(grid + cache), `metrics.py` (CDR/FPR/GMG/Wilson/McNemar/bootstrap/AUROC), `adapters.py`
(CUSUM/BSD). Cloud adapters are written to verified API schemas and import-clean, but are
**untested until creds exist** — validate with `scripts/check_creds.py` first.

> The local free guards are weak / mismatched detectors: their absolute numbers validate
> the pipeline, they are **not** the paper's result. The result comes from the commercial
> products once credentials are in.

## Still to build (after the first real cloud run)

Dilution experiment (`Proposition 2`), CUSUM/BSD adapter *evaluation* wired into
run_experiment, and figure generation — all specified in `../research/05-paper-build-spec.md`
§7-§8, §12.

## Cost & safety

- Set a **billing alert** on each cloud account before full runs (target cap
  USD 200; expect < 100). The guardrail APIs are cheap per call but the full
  grid is thousands of calls.
- `.env`, `provisioned.*.json`, model weights and results are git-ignored.
  Never commit credentials.
