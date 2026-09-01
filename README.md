# GuardGap

**Measuring what commercial LLM guardrails actually see — detector by detector — under multi-turn attacks.**

GuardGap is a vendor-agnostic harness that evaluates deployed guardrail
services (AWS Bedrock Guardrails, Azure AI Content Safety / Prompt Shields,
Google Vertex Model Armor) and open guard models against multi-turn attack
conversations. It runs each service in **detection-only mode**, captures every
internal detector's decision and confidence on every call, and reports:

- **Conversation-level detection** by attack family and inspection
  configuration (`last` turn vs. `full` transcript vs. compressed).
- **The configuration gap**, decomposed into a *configuration-induced* part (a
  deployment could fix) and a *model-induced* part (it cannot).
- **A per-detector view**: which internal filter of each product carries
  detection, and which harm families evade all of them.
- **Cost, latency, and inspected-coverage**, measured from service-reported
  usage — plus **threshold reconstruction**, so one pass recovers behaviour at
  every filter-strength setting.

It accompanies the paper *What the Guardrail Sees: Per-Detector Measurement of
Commercial LLM Guardrails under Multi-Turn Attacks*.

## Why

Enterprises buy guardrails as security controls but deploy them to inspect a
fragment of the conversation. GuardGap makes the resulting blind spots
measurable on your own tenant and configuration.

## Quick start

```bash
python -m venv .venv && . .venv/Scripts/activate      # or bin/activate on POSIX
pip install -r requirements-core.txt                  # cloud + stats (Python 3.11+)
cp .env.example .env                                  # then fill in your creds

python scripts/check_creds.py                         # verify each provider (OK / SKIP)
# obtain datasets (see DATASETS.md), then:
python scripts/build_corpora.py                       # normalise corpora
python scripts/run_experiment.py --products ready     # run everything you have creds for
python scripts/make_tables.py                         # build the tables
```

Local guard models (Prompt Guard 2, ProtectAI, Qwen3Guard) need a second
environment with PyTorch: see `requirements-local-models.txt`.

## What you provide

Your own cloud credentials and a Hugging Face token, in `.env` (never
committed). The harness provisions a detect-mode guardrail per provider
(`infra/`), then measures it. See `.env.example` for every value and where to
get it.

## Datasets

Not included — obtain them yourself (`DATASETS.md`). GuardGap normalises three
attack families (escalation, drift, fragmentation) and two benign sources into
a common schema; it never redistributes corpus text.

## Design

`guardgap/` — `schema` (conversation model), `policies` (inspection functions),
`products/` (one adapter per guardrail, uniform `score()`), `runner`
(per-product sharded cache, resumable), `metrics` (Wilson / McNemar / bootstrap
/ AUROC / gap decomposition), `report` (tables incl. per-detector),
`adapters` (CUSUM/BSD stateful wrappers), `export` (durable local dumps),
`corpora/` (dataset loaders).

## Ethics

GuardGap evaluates classifiers, not models: it replays pre-existing labelled
conversations to guardrail APIs in detection-only mode and never induces a
model to produce harmful content. It introduces no new attack technique.
Please use it only to measure and improve controls you are authorised to test,
and coordinate responsible disclosure with the affected vendors before
publishing product-named findings.

## Licence

Code: Apache-2.0 (`LICENSE`). Datasets: not included; see `DATASETS.md`.

## Citation

See `CITATION.cff` (added when the paper has a DOI).
