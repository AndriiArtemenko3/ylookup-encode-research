# Experiment log

Every run goes through `research/experiments/runner.py` into `experiments/<id>/`
and is scored ONLY by the official `research/evaluate.py`. One primary change
per experiment; controlled ablations over multi-change jumps.

| Exp | Model | Harness | Split | Pass rate | Cell acc | Cell-level | Sheet-level | Errors | Runtime | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| E000-tinker-smoke | Qwen/Qwen3.8-27B | untouched baseline | 1 task (13-1) | 0.0 | 0.68 | n/a | 0.0 | 1 parse | 106 s | plumbing OK; reply hit 8192-token cap mid-reasoning |
| E001-baseline-dev | Qwen/Qwen3.8-27B | untouched baseline | dev (60) | 0.467 | 0.747 | 0.561 | 0.263 | 25 | 18 min | 24/32 failures are 8192-token truncations |
| E002-maxtokens-24k-dev | Qwen/Qwen3.8-27B | baseline + max_tokens 24576 | dev (60) | 0.617 | 0.894 | 0.732 | 0.368 | 8 | 14 min | +9 tasks, 0 regressions; wrong values now dominant failure |
| E003-faithful-write-dev | Qwen/Qwen3.8-27B | h1-faithful-write (replay of E002) | dev (60) | 0.767 | 0.923 | 0.780 | 0.737 | 8 | 0 tokens | +9/-0; all 9 date-as-text tasks converted |
| E004-salvage-unmerge-dev | Qwen/Qwen3.8-27B | h2-salvage-unmerge (replay of E002) | dev (60) | 0.783 | 0.924 | 0.805 | 0.737 | 3 | 0 tokens | +1/-0 (38703 via unmerge); salvage recovered 4 replies |
| E006-formulas-dev | Qwen/Qwen3.8-27B | h4-formulas (coverage + formula prompt) | dev (60) | 0.700 | 0.962 | 0.780 | 0.526 | 1 | 15 min | +3/-8 NET -5: formula prompt over-applied; changes confounded |
| E007-coverage-only-dev | Qwen/Qwen3.8-27B | h5-coverage-values (coverage serialiser only) | dev (60) | 0.717 | 0.916 | 0.756 | 0.632 | 2 | 13 min | net -4 BUT 4/5 flips are sampling noise (identical prompts); true serialiser effect: -1 (250-20 cap) |

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

## E001-baseline-dev

- **Hypothesis:** measure the untouched starter baseline (pre-fine-tuning
  reference point) on the dev split.
- **Primary change (one):** none — stock harness, stock 8192 max-tokens,
  temperature 0, concurrency 4, base `Qwen/Qwen3.8-27B`.
- **Result:** pass_rate **0.467** (cell-level 0.561, sheet-level 0.263),
  cell_accuracy 0.747. 60/60 graded, 18 min, 141k in / 315k out tokens,
  mean latency 68 s/task.
- **Failure breakdown (32 failed):**
  - **24 truncated at the 8192-token cap** mid-reasoning → parse error →
    init-workbook fallback. By far the dominant mode, on both task types.
  - 7 parsed fine but produced wrong values (genuine model errors:
    32438, 333-29, 343-20, 388-47, 51680, 58942, 66-24).
  - 1 harness bug: task 38703 crashes `write_output` with
    `AttributeError: 'MergedCell' object attribute 'value' is read-only`
    (baseline writes into a merged range).
  - 0 non-truncation parse errors — when the model finishes, its JSON is fine.
- **Conclusion:** the untouched baseline's ceiling is set by the token budget,
  not by model competence: 28/35 (80%) of tasks that escaped truncation
  passed. Dev score 46.7% vs the advertised 59.0% full-400 one-shot is
  consistent with split noise plus our cap-heavy dev draw.
- **Next action:** E002 = single-variable ablation raising `--max-tokens`
  (65k context allows ~24k) on dev; also note the MergedCell write bug as a
  future harness fix (separate experiment, not bundled).

## E002-maxtokens-24k-dev

- **Hypothesis:** E001's dominant failure is the 8192-token cap; raising
  max_tokens to 24576 converts most of the 24 truncated tasks.
- **Primary change (one):** `--max-tokens` 8192 → 24576. Nothing else.
  (Concurrency 4 → 12 per adopted speed policy; independent tasks at
  temperature 0, not a result-affecting variable.)
- **Result:** pass_rate **0.617** (cell 0.732, sheet 0.368), cell_accuracy
  0.894. Diff vs E001: **FAIL→PASS 9, PASS→FAIL 0**, net +9. 14 min at
  concurrency 12, 529k output tokens, no rate-limit errors.
- **Failure breakdown (23 failed):**
  - 15 completed but wrong values — now the dominant mode.
  - 6 still truncate even at 24k (254-34, 290-27, 433-47, 49667, 524-31, 6698).
  - 1 malformed JSON (51090), 1 MergedCell harness bug (38703, persists).
- **Conclusion:** hypothesis confirmed; the cap was worth +15 points. Of
  E001's 24 truncations: 9 → pass, ~9 → completed-but-wrong, 6 → still
  truncating. Returns are diminishing — the next lever is answer quality
  (wrong values), not more tokens.
- **Next action:** analyse the 15 wrong-value traces (local, free); probe the
  6 stubborn truncators at 32k; fix the MergedCell write bug as its own
  change.

## E003-faithful-write-dev

- **Hypothesis:** the 9 "date/time-as-text" failures (E002 taxonomy pattern 1)
  are write-path representation bugs; coercing strict ISO strings to typed
  datetime/time objects in the writer converts all 9.
- **Deterministic vs fine-tuning (decided before implementing):** JSON has no
  datetime type, so the model can never hand the harness a typed date — the
  string→cell-type decision is structurally a harness responsibility.
  Fine-tuning could only relocate it (e.g. teach Excel serial emission):
  fragile, expensive, unauditable. Deterministic coercion is exact, free, and
  encodes Excel semantics rather than benchmark quirks, so it generalises to
  the holdout. Fine-tuning stays reserved for reasoning gaps (patterns 3/4).
- **Primary change (one):** `inference/write.py::coerce_value` — full-string
  ISO datetime / date / `HH:MM:SS` matches become typed objects; everything
  else (AM/PM, display formats, partial matches, invalid dates) stays
  verbatim. Baseline untouched; harness v1 = baseline + this writer.
- **Safety evidence:** regression scan found 0 ISO-pattern strings in the
  answer cells of E002's 37 passing tasks; unit checks cover the
  leave-verbatim cases.
- **Method:** replay — E002's stored responses re-written through the new
  writer (`experiments/replay.py`), then officially evaluated. Zero model
  calls, so the delta is attributable to the writer alone. Next sampled run
  revalidates end-to-end incidentally.
- **Result:** pass_rate **0.767** (cell 0.780, sheet **0.737** — doubled),
  cell_accuracy 0.923. Diff vs E002: **FAIL→PASS exactly the 9 predicted ids,
  PASS→FAIL 0.**
- **Conclusion:** taxonomy pattern 1 fully eliminated at zero token cost.
- **Next action:** remaining 14 failures = 7 serialisation-window, 4
  output-size/combinatorial, 2 logic, 1 MergedCell. E004 candidates:
  MergedCell unmerge fix (deterministic, +1) and the serialisation-coverage
  experiment.

## E004-salvage-unmerge-dev

- **Hypothesis:** two deterministic additions whose failure mode equals the
  current behaviour (init-workbook fallback / guaranteed fail) can only add:
  (a) unmerge merged ranges overlapping cells being written, (b) salvage
  complete `{"cell","value"}` entries from truncated/malformed replies.
- **Primary change:** harness v2 = h1 + `inference/parse.py::
  parse_answer_lenient` (strict first, salvage second, scanning from the last
  `"cells"` marker to skip reasoning drafts) + `_unmerge_target_ranges` in
  `inference/write.py`.
- **Method:** replay of E002's stored responses; zero tokens.
- **Result:** pass_rate **0.783** (cell 0.805, sheet 0.737), cell_accuracy
  0.9241 (from 0.9230). Diff vs E003: **FAIL→PASS 1 (38703, the unmerge fix),
  PASS→FAIL 0.** Salvage recovered 4 of the 7 parse-failed replies; none
  passed (their content was genuinely incomplete/wrong — they truncated
  mid-answer), but recovered cells lift cell_accuracy, the tie-break metric.
- **Conclusion:** both additions behaved exactly as designed; the
  no-regression property held empirically. Truncation salvage's main value
  will show on tasks that finish their JSON but stumble on syntax — rare on
  dev, cheap insurance for the holdout.
- **Next action:** remaining 13 failures: 7 serialisation-window, 4
  output-size/combinatorial, 2 logic. E005 = serialisation coverage (needs
  real sampling).

## E006-formulas-dev

- **Hypothesis:** allowing formula outputs converts the pattern-2/3 tasks
  (P006 probe: 3/11 converted, 95.7% cell accuracy on the 11 hardest).
- **Changes (two, bundled — a methodology mistake, see conclusion):**
  formula-permitting system prompt + coverage serialisation on ALL tasks
  (P005 had probed the serialiser on the 7 failing ids only).
- **Result:** pass_rate **0.700** (net **-5** vs E004's 0.783): FAIL→PASS 3
  (15671, 32438, 6698 — all never-passed-before), PASS→FAIL 8. cell_accuracy
  rose to **0.962** (best yet). Sheet-level fell 0.737 → 0.526.
- **Regression analysis:** 4/8 wrote wrong formulas where values worked
  (#N/A lookups, zero sums — prompt made formulas too attractive); 4/8 used
  no formulas but still changed answers — attributable to the serialiser
  and/or prompt wording, confounded because both changed at once.
- **Conclusion:** formula capability is real (COUNTIFS over 9.5k rows in
  1.8k tokens) but v1 of the prompt over-applies it, and bundling two
  upstream changes broke attribution. E004 (78.3%) remains the best known
  configuration.
- **Next action:** disentangle: (a) E007 = coverage serialiser alone on dev;
  (b) E008 = constrained formula prompt ("formula ONLY when direct
  computation is impractical: aggregations over many/hidden rows") + recalc
  self-check that catches error values (#NAME?/#N/A/#REF!) in answer cells
  with one retry falling back to values.

## E007-coverage-only-dev

- **Hypothesis:** isolate the coverage serialiser: E004's values-only prompt +
  h2 write path, coverage serialisation the only change.
- **Result:** pass_rate 0.717, net -4 vs E004 (FAIL->PASS: 433-47;
  PASS->FAIL: 236-22, 250-20, 333-29, 43436, 43657).
- **Key finding — sampling noise quantified:** 4 of 5 regressions and the 1
  conversion had BYTE-IDENTICAL prompts to E002 (input token counts equal;
  their sheets fit the old window, so the serialiser never touched their
  prompts). Same prompt, temp 0, different completions = Tinker sampling
  nondeterminism (SUBMISSION.md: "two runs differ by a few tasks. That is
  expected."). Fresh-sample runs carry ~±3-4 tasks (~±6pp) of run-to-run
  noise on dev; replay-based diffs (E003/E004) remain exact.
- **True serialiser effect (prompt-changed tasks only):** among passers it
  changed exactly one prompt (250-20, 2184-row sheet) and regressed it
  (bigger view -> longer reasoning -> 24k cap). Among the 7 oversize failers:
  0 conversions alone (consistent with P005). Coverage alone: <= neutral,
  slightly negative.
- **Verdict:** coverage serialiser is GATED, not default: champion 120x30
  view unless deterministic need (answer range outside 120x30, or formula
  mode active on an oversize sheet). This protects 250-20 while enabling the
  P006-class formula wins.
- **Methodology update going forward:** attribute single-run flips only where
  a mechanism is visible (prompt changed, formula present, error type);
  treat unexplained flips on identical prompts as noise. Reread of E006's 8
  regressions: the 4 no-formula ones are likely noise, the 4 formula ones
  remain real.
- **Next action:** E008 = deterministically gated formula escalation +
  recalc validation/retry (Phase B of the build spec).
