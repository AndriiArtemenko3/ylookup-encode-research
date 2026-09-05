# Experiment log

Every run goes through `research/experiments/runner.py` into `experiments/<id>/`
and is scored ONLY by the official `research/evaluate.py`. One primary change
per experiment; controlled ablations over multi-change jumps.

| Exp | Model | Harness | Split | Pass rate | Cell acc | Cell-level | Sheet-level | Errors | Runtime | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| E000-tinker-smoke | Qwen/Qwen3.8-27B | untouched baseline | 1 task (13-1) | 0.0 | 0.68 | n/a | 0.0 | 1 parse | 106 s | plumbing OK; reply hit 8192-token cap mid-reasoning |

## Template (copy per experiment)

### E00X-<slug>

- **Hypothesis:**
- **Primary change (one):**
- **Baseline compared against:**
- **Result:**
- **Regressions (PASS→FAIL from `compare.py`):**
- **Conclusion:**
- **Next action:**

## E000-tinker-smoke

- **Hypothesis:** the Tinker credentials, mandated base model, renderer and our
  experiment plumbing work end-to-end on one task.
- **Primary change (one):** none — untouched starter baseline, single task.
- **Result (2026-09-05):** end-to-end plumbing works. Attempt 1 failed on the
  key's default read-only project; attempt 2 with the team project
  (`superspreadsheets`, id in `.env` as `TINKER_PROJECT_ID`) sampled the model
  fine. Task 13-1 itself failed: 120 graded cells (sheet-level), the reply
  consumed the full 8192-token budget on visible reasoning and was truncated
  before emitting JSON → parse error → init workbook fallback (pass 0,
  cell_accuracy 0.68 coincidental). in=2392 out=8192 tokens, 106 s.
- **Conclusion:** infrastructure verified. `Qwen/Qwen3.8-27B` is a
  reasoning-heavy model; the untouched baseline's 8192 max_tokens will
  truncate many sheet-level tasks. Measure this honestly in the E001 baseline
  before changing anything (max-token budget is a candidate for the first
  controlled ablation, E002).
- **Next action:** run the untouched baseline on the dev split (E001) once
  spend is approved.
