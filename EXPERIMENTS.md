# Experiment log

Every run goes through `research/experiments/runner.py` into `experiments/<id>/`
and is scored ONLY by the official `research/evaluate.py`. One primary change
per experiment; controlled ablations over multi-change jumps.

| Exp | Model | Harness | Split | Pass rate | Cell acc | Cell-level | Sheet-level | Errors | Runtime | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| E000-tinker-smoke | Qwen/Qwen3.8-27B | untouched baseline | 1 task (13-1) | – | – | – | – | – | – | attempt 1 failed: Tinker project read-only |

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
- **Status:** attempt 1 (2026-09-05): key authenticates, `Qwen/Qwen3.8-27B`
  is on the supported-models list, but session creation fails with
  `400 This project is read-only and cannot be modified.` Blocked on
  `docs/HUMAN_ACTIONS.md` item 2 (writable project id or corrected key from
  organisers). Failed run dir removed; id reserved for the real smoke.
