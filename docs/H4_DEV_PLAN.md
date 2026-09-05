# H4 Dev Confirmation — Preregistered Plan (FROZEN before execution)

## Hypothesis
On risk-gated tasks, golden-free whole-trajectory selection over a small
candidate pool (h8 cascade artifact + 3 champion-prompt samples @ temp 0.7)
increases dev pass_rate versus the cascade alone, targeting the
healthy-but-wrong class. Offline train evidence: pass@1 78.8% → selected
82.2% (oracle 85.3%).

## Risk gate (generic observables only; NO task ids)
Fire when ANY of:
- the cascade's selected artifact is unhealthy, or any escalation stage ran;
- instruction_type == Sheet-Level Manipulation;
- answer-range cell count >= 10.

## Candidate pool and selection (frozen)
Pool = cascade artifact + 3 samples (one num_samples=3 call, champion system
prompt + champion serialisation + multisheet clause where applicable,
temperature 0.7, max_tokens 24576, h2 write path).
Features per candidate (golden-free): strict-parse, no error, response
closed (not truncated), mean pairwise cell agreement across the pool,
answered-cell count. Selection = lexicographic max over
(strict, no-error, closed, agreement, answered); **ties break to the cascade
artifact** (listed first). The cascade artifact competes as a candidate with
its own health-derived features, so the worst case per task is the cascade's
own output only when nothing scores strictly higher.

## Primary measurements (dev-60, vs E013 and E008 via compare.py)
pass_rate, cell_accuracy, cell/sheet-level, FAIL→PASS ids, PASS→FAIL ids,
gate activations, adoptions (selected != cascade artifact), runtime and token
overhead. GREEN = meaningful positive net with no broad regression channel;
YELLOW = neutral; RED = negative. No selector changes after seeing dev.
