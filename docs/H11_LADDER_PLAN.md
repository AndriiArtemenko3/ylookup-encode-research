# H11 — Adaptive Compute Ladder (Preregistered, FROZEN before any run)

## Hypothesis
Budget-bound tasks (E009 mutually-exclusive top class: 28 selected artifacts
truncated at the 24k escalation cap) convert under CONDITIONAL escalation;
unconditional global budgets waste compute and invite loops.

## FROZEN bounded policy
- Ladder: champion 24k → escalation 32k (already h8) → **one** final 40,960-
  token attempt, ONLY when: (a) the 32k attempt hit its cap (`output_tokens ==
  budget`), AND (b) progress evidence exists: the 32k attempt yielded MORE
  parsed answer cells than the 24k attempt (golden-free coverage delta), AND
  (c) context fits: prompt_tokens + 40,960 + 512 ≤ 65,536.
- Loop/stall rule: if 32k produced NO coverage increase over 24k, do NOT
  escalate; the task is reasoning-stalled, not budget-bound (route stays with
  the existing cascade selection).
- Hard stops: max 1 extra escalation per task; max aggregate 100k generated
  tokens per task; STOP_REASON recorded (solved/healthy/budget_exhausted/
  reasoning_loop/unrecoverable).

## Probe (TRAIN first)
Ids: E009-tail ∩ train ∩ truncated@24k, first 8 by sorted id. Run the h8
cascade (which already includes the 32k rung); apply the frozen 40k rung where
conditions (a)-(c) hold. Report conversions at each rung, coverage deltas,
loop-stops, tokens. GREEN = rung conversions materially exceed cost with no
regression channel (regression is structurally impossible on these ids — all
are current failures; the guard is selection-by-health as usual).

## Dev
One confirmation only if TRAIN GREEN, integrated into the combined candidate
rather than as a separate dev run if the candidate already includes h8 (the
32k rung's dev evidence arrives via any h8-based run).
