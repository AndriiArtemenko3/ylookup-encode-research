# Submission: superspreadsheets

## Team

- Team name: superspreadsheets
- Members, one GitHub handle per line:
  - AndriiArtemenko3
- Repo URL: https://github.com/AndriiArtemenko3/ylookup-encode-research

## What we built and why

<!-- FINAL PARAGRAPH PENDING E009/PHASE F — draft: -->
We kept the mandated Qwen3.8-27B untouched and rebuilt everything around it,
treating the weekend as a measured ablation study. The untouched starter
baseline scored 46.7% on our fixed 60-task dev split. Failure diagnostics — not
intuition — drove each change: 24/32 failures were token-cap truncations
(fixed by budget, +15pp); 9 were correct dates written as text against typed
golden cells (fixed by a deterministic ISO-coercion write path, +15pp, validated
by replaying stored responses at zero token cost); salvage parsing and
merged-cell handling added more. Two ideas failed honestly and are logged as
negatives: formula freedom (+3/−8 — capability real, policy wrong) and a wider
serialisation window alone (which instead measured our ±3–4 task sampling-noise
floor). Those negatives shaped the final architecture: an evidence-based
cascade that runs the proven literal-value path first, escalates to formula
mode only on golden-free distress signals (truncation, parse damage, Excel
error values in our own recalculated output), retries once with concrete
evidence, and selects the healthiest artifact with ties to the champion — so
its worst case per task is the champion's output. Dev: 46.7% → 83.3% pass,
98.4% cell accuracy, with zero regressions at every adopted step.

## Models

- Inference: `Qwen/Qwen3.8-27B` via Tinker, temperature 0, max_tokens 24576.
- Fine-tuning: <!-- none | tinker://... checkpoint + training details, pending Phase F -->

## Scores on the 400

```sh
uv run evaluate.py --predictions <your predictions.jsonl> --all --out results.json
```

```json
{"items": 400, "graded": 400, "missing": 0, "errors": 0, "pass_rate": 0.7625, "cell_accuracy": 0.3777, "pass_rate_cell_level": 0.8364, "pass_rate_sheet_level": 0.6}
```
<!-- E009 (base model + h6 cascade). May be superseded by the LoRA run E014 before hand-in. -->

## Your run on the 400

- `predictions.jsonl`: predictions.jsonl
- `outputs/`: outputs/
- `traces/`: traces/ (one `<id>.jsonl` per task; one line per model call, with
  cascade stage, health-check verdict and selection recorded per attempt)
- `run.log`: run.log

## Code

- Pipeline: `research/inference/` (cascade harness), `research/baseline/`
  (untouched starter, kept as the measured reference point).
- Docker: `Dockerfile` at repo root; reads `/data` read-only, writes `/out`;
  runs unattended.
  ```sh
  docker build -t superspreadsheets .
  docker run --rm -e TINKER_API_KEY -e TINKER_PROJECT_ID \
      -v <dataset dir>:/data:ro -v <empty dir>:/out superspreadsheets
  ```
- Environment variables: `TINKER_API_KEY`, `TINKER_PROJECT_ID` (the hackathon
  key's default project is read-only; the team project id is required).

## Things to look at

- `EXPERIMENTS.md` — the full ablation log: hypothesis, one change, diff, and
  conclusion per experiment, including the two negative results.
- `docs/BASELINE_ANALYSIS.md` — source-cited analysis of the starter baseline.
- `experiments/` — per-run manifests (git commit, params, command), official
  results.json, and event logs for every experiment.
- `research/experiments/` — the measurement tooling: runner with append-only
  experiment dirs, official-scorer diffing (FAIL→PASS buckets), failure
  diagnostics, and zero-token replay of stored responses through changed
  write paths.
- `research/tests/test_golden_isolation.py` — automated guard: inference code
  can never touch golden data; split files can never drift.
