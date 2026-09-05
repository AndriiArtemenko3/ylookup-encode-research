# Research Appendix

Compact technical narrative for judges. Every claim is backed by committed
artifacts (`EXPERIMENTS.md`, `experiments/<id>/`, manifests with git commits);
results still in flight are marked **[PENDING]** and never predicted.

## 1. Problem and objective

Mandated model: `Qwen/Qwen3.8-27B` (same for every team). Task: plain-English
instruction + workbook → the same workbook with the answer filled in; a task
passes only if **every** graded cell matches the golden workbook after
LibreOffice recalculation. Public benchmark: 400 tasks. Judges additionally run
the pipeline on a private holdout of real fund spreadsheets, so
benchmark-specific overfitting is explicitly penalised.

Design objective: improve model capability **and** inference reliability while
preserving generalisation — mechanisms over memorisation.

## 2. Evaluation discipline

Fixed, stratified, checksum-guarded splits (seed 42, frozen from the first
hour): **train 280** (goldens may drive training/reward construction),
**dev 60** (all selection decisions), **local_test 60** (untouched; single
final confirmation only). The public-400 score is the competition metric, but
after train-split optimisation it is no longer a clean generalisation estimate
— local_test is.

Practices used throughout: the official evaluator only (no custom scoring);
every experiment reports FAIL→PASS / PASS→FAIL transition tables, not just
percentages; **replay experiments** re-score stored model responses through
changed downstream code at zero cost and zero sampling noise; **matched
controls** reuse byte-identical prompts from cached traces so a diff measures
only the changed mechanism; per-run manifests record git commit, parameters,
and command. Sampling nondeterminism was measured empirically (~±3–4 tasks per
fresh dev run at temperature 0; the platform documents this) and attribution
rules were adjusted accordingly. Golden isolation is enforced by an automated
test that fails the build if inference-side code references golden data, plus
a trace audit that mechanically checks prompts for golden-value leakage
(values with init-workbook provenance excepted).

## 3. Baseline and harness progression (dev-60 unless noted)

| Exp | Mechanism (hypothesis) | Pass | Δ | Regressions | Method |
|---|---|---|---|---|---|
| E001 | untouched starter baseline | 46.7% | — | — | sampled |
| E002 | token budget 8k→24k (truncation-dominated failures) | 61.7% | +15.0 | 0 | sampled |
| E003 | typed date/time writing (evaluator type semantics) | 76.7% | +15.0 | 0 | **replay** |
| E004 | salvage parser + merged-cell unmerge | 78.3% | +1.6 | 0 | **replay** |
| E006 | formula freedom (NEGATIVE) | 70.0% | −8.3 | 8 | sampled |
| E007 | coverage serialisation alone (≈neutral; noise measured) | 71.7% | −6.6* | *mostly noise | sampled |
| E008 | evidence-based cascade (champion-first, gated escalation) | **83.3%** | +5.0 | **0** | matched-control |
| E009 | frozen cascade on the official 400 (`--all`) | **76.25%** | vs 59.0% ref | — | sampled, live |

Dev and full-400 numbers are not directly comparable (composition, whale
tasks, noise). E009 is fully audited (400/400 graded, 0 missing, trace audit
clean) and is the immutable fallback submission.

## 4. Final harness architecture (h6 cascade, shipping champion)

1. **Champion attempt**: the proven value-only configuration.
2. **Gated escalation** only on golden-free distress (truncation, parse
   damage) or provable unwinnability (answer cells outside the visible
   window / oversized output).
3. **Formula-capable route** with formula-visible workbook view and
   LibreOffice-compatibility prefixes.
4. **Health evidence**: recalculate our own output; detect Excel error
   values, static formula issues.
5. **Evidence-fed repair** (one attempt, concrete defect list).
6. **Selection**: healthiest artifact wins; ties go to the champion, so the
   worst case per task is the champion's own output.

Candidate layers built and tested locally, **[PENDING]** dev validation:
H3 structural invariants + guarded repair (train mechanism probe: 3/6 hard
targets converted, 0 control regressions); golden-free whole-trajectory
selection (offline: +3.4pp on train, 54% of the pass@4 oracle gap); targeted
patch repair; multi-sheet addressing fix (§9); H10 code-execution specialist
(§10). Key limitation stated plainly: **health checks detect distress, not
correctness** (see §7).

## 5. What failed and what we learned

**Formula freedom (E006).** Permitting formulas everywhere converted 3
never-solved tasks and improved cell accuracy to the then-best value — while
regressing 8 passing tasks (wrong formulas where literal values already
worked). Capability was real; the *policy* was wrong. This produced the
gated-escalation design instead of global formula use.

**Coverage serialisation (E007).** Showing more of the workbook alone
converted nothing: more visible data → longer reasoning → the token budget
returns as the binding constraint. The experiment's lasting value was
methodological: 4 of 5 apparent regressions ran on byte-identical prompts,
quantifying the sampling-noise floor and motivating replay/matched-control
attribution for everything after.

**First RSFT attempt (E012, strongest negative).** Rejection-sampling SFT on
verifier-approved trajectories was conceptually sound and collapsed anyway:
dev fell from 78.3% to 41.7–46.7% across three variants (2 FAIL→PASS vs 21–24
PASS→FAIL each) while training loss collapsed 0.38→0.01. Forensics: the
rollout pipeline had stored **thinking-stripped** content — median SFT target
≈253 tokens against successful trajectories of thousands — so the LoRAs
learned *answer immediately, don't reason*, and arithmetic/logic collapsed.
The hypothesis was narrowed, not erased: "RSFT on thinking-stripped targets
fails", and the corrected pipeline below exists because of this forensic.

## 6. Corrected small-data post-training methodology

**F0 trajectory-integrity gate** (training is code-forbidden until it
passes): exact prompt token ids + exact sampled completion token ids retained
per candidate; serving/training template byte-match; token round-trip
reproduces the parsed answer; verifier replay still passes; golden isolation
of decoded prompts; reasoning preservation; and a length-regime guard
(aggregate p50 ≥ 1500 tokens — the failed run's 253 is an automatic gate
failure). Measured on corrected rollouts: **p50 ≈ 4,470** completion tokens
(p10 ≈ 1,629, p90 ≈ 13,447), reasoning fraction ≈ 0.83–0.93.

Corrected RSFT design: verified successful on-policy trajectories only,
trained as exact sampled tokens (loss on completion only); LoRA rank 32;
conservative LR (1e-5 first); exposure measured in **assistant tokens**, not
epochs, with sampler checkpoints at ~25/50/100% exposure; successive-halving
evaluation on a frozen 24-task dev canary (12 stable retention sentinels + 12
opportunity tasks) with a pre-registered behaviour-collapse alarm on
completion-length distribution.

**[PENDING: corrected RSFT result]**

## 7. Residual frontier after the 76.25% champion

95 failures on the official 400, individually classified
(`docs/E009_RESIDUAL_AUDIT.md`, `experiments/E009-residual-audit.json`):

| Aggregate | n / 95 |
|---|---|
| healthy-but-wrong (passed every health check) | **53** |
| ≤5 wrong cells | 26 |
| ≥90% cell accuracy | 16 |
| large sheet-level transformations | 22 |

Mechanisms: large-output/combinatorial 26 · incomplete output 17 · unknown 15
· arithmetic/logic 12 · wrong lookup/range 12 · formula errors 6 · multi-sheet
5 · missing visibility 2.

Architectural conclusion: **over half of residual failures look healthy to the
current validator.** The next frontier is semantic uncertainty, executable
transformation, and targeted repair — not larger context windows.

## 8. Generalisation-oriented design choices

Every shipped rule encodes generic spreadsheet semantics, not benchmark
behaviour: typed Excel date/time handling; merged-cell correctness;
multi-sheet addressing; recalculation of our *own* outputs as validation;
formula-compatibility handling; parse recovery; structural invariants with a
change-allowlist guard; uncertainty-triggered retries; Python/openpyxl
execution for transformations; workbook inspection (manifests + targeted
reads) instead of ever-larger context dumps. Working rule throughout:
*a harness rule must make sense even if the engineer had never seen the golden
answer for any particular benchmark task.* Frequencies from our samples set
priorities; only mechanisms shipped.

## 9. Multi-sheet representation bug (generic, discovered by audit)

Coordinate-only answers cannot distinguish `Sheet1!B6` from `Sheet2!B6`; the
original answer schema keyed cells by coordinate alone, so multi-sheet answer
ranges with overlapping coordinates (5 public tasks; stable 100%-reproducible
residuals on two train tasks were this bug's signature) silently stamp one
sheet's values everywhere. Fix: sheet-qualified addresses (`"Sheet2!B6"`)
with `(sheet, coordinate)` keying; single-sheet format unchanged
byte-for-byte; the prompt requires qualification only when the answer range
spans sheets. Unit-tested (same coordinate, two sheets, distinct values; old
format regression-free). Holdout relevance is high — real fund workbooks are
multi-sheet by construction. **[PENDING: scored validation]**

## 10. Inference-time code execution (H10, specialist route)

Motivation: emitting thousands of literal cells is the wrong representation
for sort/filter/join/dedupe/fill transformations (26 residual failures are
large-output/combinatorial; 22 are large sheet transforms; two "whale" tasks
grade >95k cells each). Architecture: compact workbook manifest → model writes
a Python/openpyxl program → sandboxed execution on a copy (no network,
timeout-killed, env-stripped) → output workbook → health/structural validation
→ one traceback-fed code repair. Deliberately a *gated specialist*, not a
general agent framework. Local self-tests pass (execution, timeout, crash
capture, network denial). **[PENDING: H10 mechanism/DEV result]**

## 11. Reproducibility and integrity

`EXPERIMENTS.md` (every experiment: hypothesis, one change, transitions,
conclusion — negatives retained verbatim); per-run `experiments/<id>/`
manifests (git commit, command, parameters) with official `results.json`;
required contract artifacts (`predictions.jsonl`, `outputs/`, `traces/`,
`run.log`) from the audited E009 run; `Dockerfile` cold-tested against the
judges' contract on a goldenless dataset copy; golden-isolation and
split-integrity tests; trace audit tooling; F0 trajectory-integrity tests;
frozen split and canary files. Negative experiments (E006, E007, E012) are
committed history, not rewritten.

## 12. Final results

| Metric | Value |
|---|---|
| Reference one-shot, public 400 | 59.0% |
| Base model + our harness, public 400 (E009) | **76.25%** (cell-level 83.6%, sheet-level 60.0%) |
| Final model + harness, public 400 | **[PENDING]** |
| Held-out local_test (single confirmation) | **[PENDING]** |

## 13. Key takeaways

1. Most of the initial gap was inference-system failure, not missing model
   knowledge: +31.6 dev points came from deterministic writing, budget, and
   escalation policy before any training.
2. Deterministic spreadsheet semantics (typed dates, unmerge, salvage) were
   the largest *and safest* gains — zero regressions, replay-provable.
3. Global capability grants (formula freedom) hurt; evidence-gated escalation
   captured the upside without the regressions.
4. Small-data post-training is acutely sensitive to trajectory
   representation: stripping reasoning from targets destroyed the policy;
   preserving the exact sampled tokens is part of the training-data contract.
5. The remaining frontier is healthy-but-wrong semantic error (53/95),
   motivating golden-free selection, targeted repair, and executable
   transformations rather than more context.
