# Research plan — SpreadsheetBench Verified, research track

Goal: maximise `pass_rate` (all graded cells match golden after LibreOffice
recalculation) of the mandated small model on the 400 public tasks, while
preserving generalisation to the judges' private holdout of real fund
spreadsheets. Secondary metric: `cell_accuracy`.

## Invariants (never violated)

1. `research/evaluate.py`, `research/sb.py` scoring semantics, benchmark golden
   workbooks and metadata are immutable reference code/data.
2. Golden workbooks are readable ONLY by evaluation and (later) training-data
   construction. Never by the inference pipeline, agent tools, prompts, or any
   runtime retrieval. `research/tests/test_golden_isolation.py` enforces this.
3. No golden values in inference prompts, runtime traces, or telemetry.
4. No task-id → answer lookups anywhere.
5. Split files in `research/splits/` are frozen; never regenerated.
6. Secrets live in `research/.env` (gitignored) and are never printed or
   committed.
7. No material Tinker/API credit spend without explicit human approval.

## Phases

| Phase | What | Gate to next |
|---|---|---|
| P0 (this) | Environment, oracle, splits, experiment framework, telemetry, baseline analysis | oracle 1.0/1.0; docs done |
| P1 | Confirm model id; Tinker one-task smoke (E000); untouched baseline on dev split, then full 400 | human confirms model + approves spend |
| P2 | Failure analysis of baseline with `research/experiments/compare.py` | failure taxonomy written |
| P3 | Harness experiments (one change per experiment): serialisation with formulas, targeted range reads, code execution, validation + retry/self-correction | dev-split gains without local_test regression |
| P4 | Tinker post-training on train-split-derived data (goldens allowed here only) | approved budget; P3 harness frozen enough |
| P5 | Docker packaging against the `/data` → `/out` contract; full-400 run; SUBMISSION.md | Sun 12:00 deadline |

## Module boundaries (for clean containerisation and golden isolation)

```
research/
  evaluate.py, sb.py          official scorer — do not modify
  baseline/                   untouched starter baseline (reference point)
  inference/                  (future) improved harness — NEVER reads goldens
  tools/                      (future) agent tools (workbook inspect, code exec) — NEVER read goldens
  training/                   (future) training-data construction — MAY read train-split goldens
  telemetry.py                optional OTel + local events.jsonl — no goldens, no secrets
  experiments/                experiment framework (manifest, runner, compare)
  splits/                     frozen train/dev/local_test id lists
  tests/                      golden-isolation and split-integrity checks
experiments/                  run artifacts, one dir per experiment id (E000-..., E001-...)
```

The final submission container will wrap `inference/` (+ `tools/`) only, reading
`/data` read-only and writing `predictions.jsonl`, `outputs/`, `traces/`,
`run.log` to `/out`.

## Splits

Fixed, stratified by instruction_type, seed 42 (`research/splits/make_splits.py`):

- `train` 280 (193 cell / 87 sheet) — goldens may build training data later
- `dev` 60 (41 / 19) — iteration set for harness/prompt/hyperparameters
- `local_test` 60 (41 / 19) — held out; occasional generalisation checks only

The official full-400 score is always reported separately with
`uv run evaluate.py --predictions ... --all`.

## Experiments

Every run goes through `research/experiments/runner.py` into
`experiments/<id>/` with a `manifest.json` (git commit, model, prompt version,
split, sampling params, command, runtime), the four official artifacts,
`results.json` from the official evaluator, and `events.jsonl`. Log in
`EXPERIMENTS.md`: hypothesis, one primary change, result, regressions,
conclusion, next action. Controlled ablations over multi-change jumps.

## Mandated model — CONFIRMED

`Qwen/Qwen3.8-27B` (human-confirmed 2026-09-05; matches slides' "Qwen3.8-27B,
59.0% one-shot"). tinker-cookbook renderer: `qwen3_8_xhigh_reasoning` — a
reasoning model, so budget max_tokens for thinking and rely on the renderer's
`<think>` handling already present in `baseline/common.py`.

## Tinker smoke test (prepared, not run — blocked on HUMAN_ACTIONS #2, API key)

```sh
cd research && uv run baseline/tinker_predict.py \
    --out-dir ../experiments/E000-tinker-smoke/raw \
    --base-model Qwen/Qwen3.8-27B --ids 13-1 --concurrency 1
```
