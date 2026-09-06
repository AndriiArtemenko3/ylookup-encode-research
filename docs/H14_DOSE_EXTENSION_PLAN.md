# H14 — RLVR dose extension (preregistered, NOT launched before submission)

**Hypothesis (separate from evaluation power):** H13A/H13C may have been
under-trained in optimization depth — 20 and 14 optimizer updates
respectively. H14 tests dose, changing nothing else.

## Frozen design

- Same H13A environment, task population (51 frozen boundary groups), reward
  (R0), K=8, LoRA rank 32, LR 1e-5, max_tokens 16384, renderer, verifier.
- **Continue from the durable H13A final checkpoint**
  (`tinker://23e9d74e-b453-551d-9e73-3e8249595f93:train:0/weights/final`,
  optimizer state included via cookbook `state_path`) by re-invoking
  `training/h13_run.py` against the same `experiments/H13A-online-rlvr`
  log path with `n_batches` extended to 100 — cookbook rl.train resumes
  after the last checkpoint in `checkpoints.jsonl`. If exact optimizer
  resume turns out unsupported, fall back to weights-only continuation and
  **document that deviation explicitly**; do not silently restart.
- Target ~100 total optimizer updates; checkpoints every 20 (save_every=20
  equivalent — keep the existing save cadence if changing it would break
  resume).
- NO dev-driven tuning. Evaluation at preregistered checkpoints only:
  frozen canary24 for safety, then dev60 at ~60 and ~100 updates if
  non-destructive. local_test is never reused.

## Launch condition

Only after the submission form is filed and packaging is verified — H14 must
not contend with submission-critical work. Results are post-submission
research / live-judging evidence, never retroactive submission claims.

## Interpretation guardrails

Constructive = exact-task movement (dev60 net vs the E013 control), not
training reward. The anti-p-hacking rule from the promotion gate applies:
no LR/reward/rank/population changes in response to interim results.
