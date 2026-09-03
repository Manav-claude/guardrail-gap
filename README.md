# GuardGap

**Measuring what commercial LLM guardrails actually see, detector by detector, under multi-turn attacks.**

GuardGap is a vendor-agnostic harness that evaluates deployed guardrail
services (AWS Bedrock Guardrails, Azure AI Content Safety text analysis and
Prompt Shields, Google Vertex AI Model Armor) and open guard models against
multi-turn attack conversations. It runs each service in **detection-only
mode**, captures every internal detector's decision and confidence on every
call, and reports:

- **Conversation-level detection** by attack family and inspection
  configuration (`last` turn vs. `full` user history vs. `m2s`, the
  multi-turn-to-single-turn *hyphenize* template).
- **The configuration gap**, decomposed into a *configuration-induced* part (a
  deployment could fix) and a *model-induced* part (it cannot), plus the
  **per-decision** view that explains why the aggregate gap is negative.
- **A per-detector view**: which internal filter of each product carries
  detection, and which harm families evade all of them.
- **Threshold reconstruction**: because responses grade each detector, one
  pass at maximum sensitivity recovers behaviour at every filter strength.
- **Cost, latency, and inspected coverage** from service-reported usage.

It accompanies the paper *What the Guardrail Sees: Per-Detector Measurement of
Commercial LLM Guardrails under Multi-Turn Attacks* (IEEE ACDSA 2027,
submitted). The aggregate results reported in the paper are in
`results_public/` (rates, counts, and definitions only; no conversation text).

## Quick start

```bash
python -m venv .venv                      # core env: cloud SDKs + statistics (Python 3.11+)
# activate it (Windows: .venv\Scripts\activate ; POSIX: . .venv/bin/activate)
pip install -r requirements-core.txt
cp .env.example .env                      # fill in your own credentials

python scripts/check_creds.py             # OK / SKIP / FAIL per provider
python scripts/download_datasets.py       # fetch the corpora into data/raw (see DATASETS.md)
python scripts/build_corpora.py           # normalise them
python scripts/run_experiment.py --products bedrock,azure_prompt_shields,azure_text,model_armor --no-report
python scripts/make_tables.py             # console tables + results/
python scripts/make_public_results.py     # aggregate CSVs incl. Wilson CIs, strength curve, per-detector
python scripts/eval_cusum.py              # stateful-adapter evaluation at matched FPR budgets
```

The open guard models (Prompt Guard 2, ProtectAI DeBERTa v2, Qwen3Guard-0.6B)
need a second environment with PyTorch (`requirements-local-models.txt`); run
them with `--products local` from that environment. `--products ready` selects
every product whose credentials (and, for local models, torch) are present.
Every call is cached per product in `cache/scores_<product>.sqlite`, so runs
are resumable. See `RUNNING.md` for the exact sequence used for the paper.

## Operating points used in the paper

| Product | Setting during the run | Reconstructed afterwards |
|---|---|---|
| Bedrock Guardrails | six content filters at strength HIGH, eight author-defined denied topics, all actions NONE (detect-only) | MEDIUM and LOW strengths; content-only (no topics) |
| Model Armor | template at LOW_AND_ABOVE, all filters | MEDIUM_AND_ABOVE, HIGH |
| Azure Content Safety text | severity >= 2 counted as detection (`AZURE_TEXT_BLOCK_SEVERITY`, default 2; Azure's own default is 4) | severity >= 4, >= 6 |
| Prompt Shields | binary `attackDetected` | none possible |

Bedrock ships no default denied-topic list; the eight definitions used are in
`infra/aws_provision_guardrail.py` and `results_public/bedrock_denied_topics.json`.

## What you provide

Your own cloud credentials and a Hugging Face token, in `.env` (never
committed). The scripts under `infra/` provision the exact detect-mode
guardrail / template used in the paper. See `.env.example` for every value.

## Datasets

Not included; obtain them yourself with `scripts/download_datasets.py`
(`DATASETS.md` lists sources, licences and the expected layout). The three
attack families are `escalation`, `drift`, and `coreference`; the last is the
CoSafe coreference corpus (not a decomposition/fragmentation corpus).

## Layout

`guardgap/` - `schema` (conversation model), `policies` (inspection functions
`last` / `full` / `m2s`), `products/` (one adapter per guardrail, uniform
`score()`), `runner` (per-product sharded cache, resumable), `metrics`
(Wilson / McNemar / bootstrap / AUROC / gap decomposition), `report` (tables
incl. per-detector), `export` (durable local dumps), `corpora/` (loaders).
`guardgap/adapters.py` (CUSUM/BSD) is evaluated by `scripts/eval_cusum.py`.
`guardgap/products/llama_guard4.py` is an adapter for a hosted Llama Guard and
was **not** evaluated in the paper.

## Ethics

GuardGap evaluates classifiers, not models: it replays pre-existing labelled
conversations to guardrail APIs in detection-only mode and never induces a
model to produce harmful content. It introduces no new attack technique.
Please use it only to measure and improve controls you are authorised to test,
and coordinate responsible disclosure with the affected vendors before
publishing product-named findings.

## Licence and citation

Code: Apache-2.0 (`LICENSE`). Datasets: not included; see `DATASETS.md`.
To cite, see `CITATION.cff`.
