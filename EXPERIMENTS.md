# Experiment log

Every run goes through `research/experiments/runner.py` into `experiments/<id>/`
and is scored ONLY by the official `research/evaluate.py`. One primary change
per experiment; controlled ablations over multi-change jumps.

| Exp | Model | Harness | Split | Pass rate | Cell acc | Cell-level | Sheet-level | Errors | Runtime | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| E000-tinker-smoke | TBC (blocked: model id + TINKER_API_KEY) | untouched baseline | 1 task (13-1) | – | – | – | – | – | – | prepared, not run |

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
- **Status:** blocked on `docs/HUMAN_ACTIONS.md` items 1 (model id) and 2
  (TINKER_API_KEY). Command prepared in `docs/RESEARCH_PLAN.md`.
