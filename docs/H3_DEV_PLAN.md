# H3 Dev Confirmation — Preregistered Plan (FROZEN before execution)

Frozen as of commit 612ee70 lineage; no rule/threshold/prompt changes after
this document until the dev run is scored.

## Primary hypothesis
Generic structural validation + guarded repair (invariants.py R1/R1b/R2 with
the changed-cells acceptance guard, exactly as committed) increases dev
pass_rate without material PASS→FAIL regression.

## Frozen components
- `research/inference/invariants.py` (R1 completeness ≥0.3 fill + row-activity;
  R1b all-empty; R2 column-type consistency, init-aware, header-protected)
- acceptance guard in `research/inference/cascade.py` (defects strictly
  decrease AND changes ⊆ flagged ∪ previously-empty)
- `STRUCTURAL_HINT` repair prompt, escalation budget 32k, h8-structural.

## Train mechanism evidence (already recorded)
3/6 hard-target conversions (120-24, 398-14, 73-45), 0/2 control regressions.

## Primary measurements (dev-60 vs E008 via compare.py)
FAIL→PASS · PASS→FAIL · net · cell-level · sheet-level · repair-trigger count
and precision · added inference cost. Success: net > 0 with PASS→FAIL ≈ 0.
No tuning against individual dev failures afterwards.

## Ready command (DO NOT run while F1v2 rollouts hold Tinker concurrency)
```sh
cd research && uv run experiments/runner.py --id E013-h3-dev --split dev \
  --model Qwen/Qwen3.8-27B --harness h8-structural --prompt-version cascade-v1 \
  --temperature 0 --max-tokens 24576 --concurrency 12 --retry-policy "escalate+structural" -- \
  uv run inference/cascade_predict.py --out-dir "{out_dir}" --base-model Qwen/Qwen3.8-27B \
  --ids "{ids}" --concurrency 12 --max-tokens 24576 --champion-cache ../experiments/E002-maxtokens-24k-dev
```
(Champion-cache = matched control on stage-1; repair/escalation sample live.)
