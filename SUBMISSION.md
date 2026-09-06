# Submission: superspreadsheets

## Team

- Team name: superspreadsheets
- Members, one GitHub handle per line:
  - AndriiArtemenko3
- Repo URL: https://github.com/AndriiArtemenko3/superspreadsheets-ylookup-encode

## What we built and why

We kept the mandated Qwen3.8-27B untouched and rebuilt everything around it,
treating the weekend as a measured ablation study. The untouched starter
baseline scored 46.7% on our fixed 60-task dev split. Failure diagnostics — not
intuition — drove each change: 24/32 failures were token-cap truncations
(fixed by budget, +15pp); 9 were correct dates written as text against typed
golden cells (fixed by a deterministic ISO-coercion write path, +15pp, validated
by replaying stored responses at zero token cost); salvage parsing,
merged-cell handling and sheet-qualified multi-sheet addressing added more.
Ideas that failed are logged as honest negatives: formula freedom as a policy
(+3/−8 — capability real, policy wrong), a wider serialisation window alone
(which instead measured our ±3–4 task sampling-noise floor), best-of-N
trajectory selection (net −3: blind candidates outvote sighted artifacts), and
a post-training arc (RSFT, reward-function ablation, online RLVR) that was
uniformly safe but never beat the harness — including the diagnosis that
thinking-stripped SFT targets, not RSFT itself, caused a 30-point collapse.
Those negatives shaped the final architecture: an evidence-based cascade that
runs the proven literal-value path first, escalates to a formula-permitting
32k-budget mode only on golden-free distress signals (truncation, parse
damage, Excel error values in our own recalculated output), retries once with
concrete evidence, applies one structural-invariant repair behind a
changed-cells allowlist, and selects the healthiest artifact with ties to the
champion — so its worst case per task is the champion's output. Dev: 46.7% →
85.0% pass; single-use local_test confirmation: 91.7%.

## Models

- Inference: `Qwen/Qwen3.8-27B` via Tinker, temperature 0; 24576-token
  champion budget with a gated 32768-token escalation rung.
- Fine-tuning: none in the submitted configuration. We trained and measured
  five LoRA post-training variants (corrected-representation RSFT at two LRs,
  three reward-function REINFORCE arms) plus a true online-RLVR run; all were
  safe on matched canaries but none beat the frozen harness on dev, so the
  base model ships. Full designs, checkpoints and negative results:
  `docs/RESEARCH_APPENDIX.md`. <!-- update if H13A/H13B promotes -->

## Scores on the 400

```sh
uv run evaluate.py --predictions <your predictions.jsonl> --all --out results.json
```

```json
{"items": 400, "graded": 400, "missing": 0, "errors": 0, "pass_rate": 0.78, "cell_accuracy": 0.386, "pass_rate_cell_level": 0.8364, "pass_rate_sheet_level": 0.656}
```
<!-- E015: frozen finalist (base model + h8 cascade), single Sacred-400
measurement run 2026-09-06, trace-audited clean (no golden content in any
prompt). Earlier champion E009 (h6): 76.25% — kept in experiments/ as the
measured intermediate. -->

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

- `docs/RESEARCH_APPENDIX.md` — concise research narrative covering the
  benchmark methodology, ablations, negative results, post-training design,
  residual-error analysis and generalisation safeguards.
- `EXPERIMENTS.md` — the full ablation log: hypothesis, one change, diff, and
  conclusion per experiment, including the negative results.
- `docs/BASELINE_ANALYSIS.md` — source-cited analysis of the starter baseline.
- `experiments/` — per-run manifests (git commit, params, command), official
  results.json, and event logs for every experiment.
- `research/experiments/` — the measurement tooling: runner with append-only
  experiment dirs, official-scorer diffing (FAIL→PASS buckets), failure
  diagnostics, and zero-token replay of stored responses through changed
  write paths.
- `research/tests/test_golden_isolation.py` — automated guard: inference code
  can never touch golden data; split files can never drift.
