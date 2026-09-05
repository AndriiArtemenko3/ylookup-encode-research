# Experiment log

Every run goes through `research/experiments/runner.py` into `experiments/<id>/`
and is scored ONLY by the official `research/evaluate.py`. One primary change
per experiment; controlled ablations over multi-change jumps.

| Exp | Model | Harness | Split | Pass rate | Cell acc | Cell-level | Sheet-level | Errors | Runtime | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| E000-tinker-smoke | Qwen/Qwen3.8-27B | untouched baseline | 1 task (13-1) | – | – | – | – | – | – | blocked: TINKER_API_KEY |

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
- **Status:** model confirmed (`Qwen/Qwen3.8-27B`); blocked only on
  `docs/HUMAN_ACTIONS.md` item 2 (TINKER_API_KEY). Command prepared in
  `docs/RESEARCH_PLAN.md`.
