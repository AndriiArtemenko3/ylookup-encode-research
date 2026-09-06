# Data lineage index

Everything data-shaped in this submission, where it lives, and what may be
claimed about it.

## A. Benchmark source data

The public benchmark (400 SpreadsheetBench-Verified tasks: init workbooks,
instructions, golden answers) is downloaded by `research/data/download.py`
into `research/data/` and is **not vendored into Git** — it is the
organizers' distribution, reconstructible by the script, and vendoring golden
answers into a public repo would leak evaluation data. Everything below is
*our derived data*, which is committed.

## B. Frozen evaluation splits (`research/splits/`)

| File | N | Purpose |
|---|---|---|
| `train.json` | 280 | training-side research only: rollouts, reward construction, mechanism probes |
| `dev.json` | 60 | repeated controlled validation of one-change hypotheses |
| `local_test.json` | 60 | held out untouched; evaluated exactly once after finalist freeze (91.67%) |
| `canary24.json` | 24 | frozen safety canary for trained checkpoints: 12 sentinels + 12 opportunity tasks |
| `make_splits.py` | — | deterministic seed-42 construction with checksum guards |

## C. Offline post-training corpora (committed)

| File | Examples | Size | What it is |
|---|---|---|---|
| `experiments/F1-rollouts/sft_dataset.jsonl` | uniform curation | 1.7 MB | first-generation RSFT corpus — **thinking-stripped representation; caused the E012 collapse; retained as the negative-result artifact** |
| `experiments/F1-rollouts/sft_dataset_hard.jsonl` | hard-oversampled variant | 2.3 MB | same generation, learnable-band oversampling |
| `experiments/F1-rollouts/groups.jsonl` | — | 23 KB | per-task rollout group metadata for the above |
| `experiments/F1v2-rollouts-reasoning-preserved/sft_dataset_v2.jsonl` | 253 | 10.8 MB | **corrected reasoning-preserved RSFT corpus**: exact raw sampled tokens (prompt+completion ids), verifier-approved, F0 trajectory-integrity-gated (p50 ≈ 4.5k completion tokens vs 253 in the failed corpus) |
| `experiments/F1v2-rollouts-reasoning-preserved/sft_dataset_h13b.jsonl` | 100 | 5.9 MB | hard-mined expert-iteration corpus for H13B (frozen before training) |
| `experiments/F1v2-rollouts-reasoning-preserved/groups.jsonl` | — | 23 KB | rollout group metadata for the corrected pipeline |

Raw per-candidate rollout stores (`experiments/*/rollouts/`) are gitignored
for size; the curated corpora above, plus group metadata, are the durable
training evidence.

## D. Online RLVR lineage (H13A / H13C)

These arms have **no static training dataset by design** — every update uses
fresh current-policy rollouts. Their reproducibility surface, all committed:

- Frozen task populations: `experiments/H13A-online-rlvr/frozen_tasks.json`
  (51 boundary groups) and `experiments/H13C-fulltrain-rlvr/frozen_tasks.json`
  (269 sampleable of 280 train tasks; the 11 excluded whale observations are
  listed with their token counts).
- Checkpoints: `experiments/*/checkpoints.jsonl` (durable Tinker
  `state_path`/`sampler_path` per save).
- Per-update metrics: `experiments/*/metrics.jsonl` (H13C's file contains 3
  leading rows from the crashed first launch, then the guarded restart —
  documented in `docs/H13C_FULLTRAIN_PLAN.md`).
- Environment + reward: `research/training/h13_env.py`, `h13c_env.py`
  (routing, R0 reward via the official scorer, train-only enforcement).
- Launchers/config: `research/training/h13_run.py`, `h13c_run.py`.

## E. Submission evaluation artifacts (repo root)

`predictions.jsonl`, `outputs/`, `traces/`, `run.log` — the four
runtime outputs of the E015 submission run — plus `results.json`, our scored
public-400 evidence (78.0%, 400/400 graded). The runtime container never
produces `results.json` itself: scoring requires goldens, which inference
never has.

## F. Data isolation

Golden values are readable only by the official evaluator and TRAIN-side
reward construction — never by runtime inference (enforced by
`research/tests/test_golden_isolation.py` and audited over both full-400
runs' traces by `research/experiments/audit_traces.py`: clean). The
organizers' private holdout has never been seen by anything in this
repository.
