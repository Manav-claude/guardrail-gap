# Publishing to GitHub — safety checklist

Run this the day you open-source the repo (after the cloud runs finish). The
goal: publish the **measurement code**, never the **secrets** or the
**datasets**.

## 1. Confirm nothing secret or licensed is tracked

```
# from experiment/, after git init:
git init && git add -A && git status
```
Then verify NONE of these appear in "Changes to be committed":
- [ ] `.env` (real secrets) — only `.env.example` should be tracked
- [ ] any `project-*.json`, `*-key.json`, `service-account*.json` (cloud keys)
- [ ] `data/` (raw or normalized corpora — third-party, some harmful)
- [ ] `models/` (downloaded weights)
- [ ] `cache/`, `results/scores_full.*`, `results/shards_backup/`,
      `results/scores_backup.sqlite` (per-call stores)
- [ ] `provisioned.*.json`

The `.gitignore` already excludes all of the above; this is the belt-and-braces
check. If any appear, STOP and fix `.gitignore` before the first commit.

## 2. Scrub history / hard-coded IDs

- [ ] `grep -rn "hf_\|AKIA\|sk-\|BEARER\|Ocp-Apim" .` returns nothing in tracked files.
- [ ] No account IDs, ARNs, endpoints, or project ids in committed code
      (they belong in `.env`). `provisioned.aws.json` is git-ignored.
- [ ] Replace the LICENSE placeholder note with the full Apache-2.0 text.

## 3. What SHOULD be published

- All of `guardgap/` (schema, policies, products, runner, metrics, adapters,
  report, export, corpora loaders)
- `scripts/` (run_experiment, make_tables, check_creds, build_corpora)
- `infra/` (provisioning scripts — they read creds from `.env`, contain none)
- `requirements-core.txt`, `requirements-local-models.txt`
- `.env.example`, `.gitignore`, `LICENSE`, `README.md`, `DATASETS.md`
- Aggregate results only, if desired: `results/table*.csv`,
  `results/detector_*.csv` (detection rates + per-detector tables; these
  reference conversations by id and contain no attack text). Decide per your
  disclosure timeline.

## 4. What must NOT be published

- Any credential or key file; the corpora (raw or normalized); model weights;
  the full per-call stores (`scores_full.*`, shard `.sqlite`) — these are
  regenerable and large, and while their `raw_json` holds detector verdicts
  (not attack text), keep them out unless you have reviewed them.

## 5. Recommended repo metadata

- [ ] `README.md` = the public overview (see README_public.md; rename on publish)
- [ ] Topics: `ai-security`, `llm-guardrails`, `red-teaming`, `content-moderation`
- [ ] A `CITATION.cff` pointing at the paper once it has a DOI
- [ ] Responsible-disclosure note in the README (vendors were notified)
