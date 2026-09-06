# README FACT PACK (source-of-truth, 2026-09-06 ~09:25)

Every number below is read from committed artifacts (path cited). Not a
README draft. Conversational memory was not used where a file exists.

## 1. Final measured results

| Metric | Value | Source |
|---|---|---|
| **E015 full-400 exact pass** | **78.0% = 312/400** | `results.json` (repo root; copy of `experiments/E015-finalist-400/results.json`) |
| E015 cell_accuracy | 0.386 | same |
| E015 cell-level pass rate | 0.8364 | same |
| E015 sheet-level pass rate | 0.656 | same |
| E015 items/graded/missing/errors | 400 / 400 / 0 / 0 | same |
| E013 dev (finalist config) | 85.0% (51/60), cell_acc 0.9807, cell-lvl 0.878, sheet-lvl 0.7895 | `experiments/E013-h3-dev/results.json` |
| local_test (single-touch) | 91.67% (55/60), cell_acc 0.969, cell-lvl 0.9268, sheet-lvl 0.8947 | `experiments/P8-localtest-finalist/results.json` |
| E009 (prior champion, fallback) | 76.25% (305/400), cell_acc 0.3777, sheet-lvl 0.600 | `experiments/E009-champion-400/results.json` |
| Reference one-shot on the 400 | 59.0% — **organizer-advertised, not re-measured by us** | cited in `docs/RESEARCH_PLAN.md:76`, `EXPERIMENTS.md:71` |
| E009→E015 transitions | 22 FAIL→PASS / 15 PASS→FAIL / net +7 | `EXPERIMENTS.md` morning table (compare.py on both results.json) |

## 2. Final submission architecture (as executed by E015)

Ordered path per task (`research/inference/cascade.py`, HARNESS_VERSION
`h8-structural`; run cmd in `experiments/E015-finalist-400/manifest.json`):

1. **Champion attempt**: values-only system prompt + baseline 120×30
   `data_only` serialization (`baseline/common.py`), temperature 0,
   **max_tokens 24576**. Skipped only on provable unwinnability:
   answer range > 300 cells (`LARGE_ANSWER_CELLS`) or answer cells outside
   the 120×30 serialized view (`doomed_reason`).
2. **Golden-free health checks** on our own artifact: truncation, strict→
   salvage parse damage, static formula issues, Excel error values after
   recalculating **our own output** (`inference/health.py`; goldens never
   read).
3. **Gated escalation** (only on distress or doomed): coverage serializer
   (CHAR_BUDGET 100k chars, formula-visible "value [=formula]" with
   all→answer-cols→none ladder, `inference/serialize.py`) + formula-permitting
   system prompt, **max_tokens 32768**; then one **evidence-fed repair**
   attempt quoting the concrete defect list.
4. **Structural invariants** (`inference/invariants.py`): requested-range
   emptiness (fill-ratio + row-activity + all-empty), column-type
   consistency (init-aware, header-protected) → at most one **guarded
   structural repair** whose writes are restricted to a changed-cells
   allowlist (`inference/patch.py` guard in cascade).
5. **Selection**: healthiest artifact by hard-failure count; ties → champion
   (worst case per task = champion output).
6. **Writer** (`inference/write.py`): ISO date/time → typed cells, `_xlfn`
   formula prefixing, merged-range unmerge before write, salvage JSON parser
   behind strict parse; **sheet-qualified addresses** (`Sheet2!B6`) with
   `(sheet, coord)` keys whenever the answer range spans sheets; LibreOffice
   recalculation applied to formula-bearing outputs.

## 3. Key ablations (dev n=60 unless noted; committed in EXPERIMENTS.md)

| Exp | Primary change | Split | Before | After | F→P | P→F | Verdict |
|---|---|---|---|---|---|---|---|
| E001 | untouched starter baseline | dev | — | 46.7% | — | — | measured floor |
| E002 | token budget 8k→24k | dev | 46.7 | 61.7% | +9 | −0 | adopted |
| E003 | typed write (ISO dates→dates) | dev | 61.7 | 76.7% | +9 | −0 | adopted (replay-validated) |
| E004 | salvage parser + unmerge | dev | 76.7 | 78.3% | +1 | −0 | adopted |
| E006 | formulas everywhere | dev | 78.3 | 70.0% | +3 | −8 | **negative** (capability real, policy wrong) |
| E007 | coverage view alone | dev | 78.3 | 71.7% | +1 | −5 | **negative** (measured ±3–4 noise floor) |
| E008 | evidence cascade | dev | 78.3 | 83.3% | +3 | −0 | adopted |
| E013 | structural repair + multi-sheet (h8) | dev | 83.3 | 85.0% | +2 | −1 | adopted → **finalist** |
| E014 | H4 risk-gated best-of-N | dev | 83.3 | 80.0% | +1 | −4 | **negative** (blind candidates outvote sighted artifacts) |
| E009 | champion (h6) on official 400 | 400 | — | 76.25% | — | — | measured; fallback |
| E015 | frozen finalist on official 400 | 400 | 76.25 | **78.0%** | 22 | 15 | **submission run** |

## 4. Post-training facts (all Qwen/Qwen3.8-27B, LoRA rank 32)

| Family | Objective | LR | Population | Reward | Canary (frozen 24: 12 sentinels + 12 opportunity; base control 12/12 + 2/12) | Constructive exact-pass gain? |
|---|---|---|---|---|---|---|
| Corrected RSFT ×2 (`F1v2-sft-lr1e5/2e5`) | verifier-approved on-policy SFT, raw-token targets, 253 examples, 1 pass (1,799,795 assistant tokens) | 1e-5, 2e-5 | train rollouts (F0-gated) | n/a | 12/12 sent; 2/12 opp (both LRs) | **No** — control-level |
| H12-R0/R1/R2 (`pg_train.py`) | on-policy REINFORCE, signed-advantage weighted CE, clip ±2, 4 groups/step | 1e-5 | 51-group frozen variance band | R0 continuous / R1 discrete / R2 hybrid | R0 13/24 (1/12 opp), R1 13/24 (1/12), R2 14/24 (2/12) | **No** — all ≤ control |
| H13B (`H13B-hardmined-rsft`) | hard-mined expert-iteration RSFT, 100 frozen examples, 2 passes (2,096,350 assistant tokens) | 2e-5 | hard-mined train successes | n/a | 13/24 = 12/12 sent, 1/12 opp | **No** — one below control |
| H13A **IN-FLIGHT** | true online RLVR (cookbook rl.train, importance sampling, fresh rollouts, K=8, 20 steps) | 1e-5 | 51 frozen boundary groups | R0 (1.0 / 0.2·acc / −0.1) | step-8: 14/24 = 12/12 sent + **the same 2/12 opp tasks as base control** | not at step 8; final canary pending |
| H13C **IN-FLIGHT** | online RLVR, full-train coverage (269/280 sampleable, 11 whale observations excluded+listed, K=4, 14 updates) | 1e-5 | all sampleable train | R0 | none yet | pending |

Cross-family fact: sentinel retention is 12/12 in every arm (zero capability
collapses after the F0 trajectory-integrity fix); no arm has exceeded the
base control's 2/12 opportunity passes.

## 5. Generalisation / evaluation discipline

- Splits (`research/splits/`, seed 42, checksum-guarded): train 280 / dev 60 /
  local_test 60. **local_test was touched exactly once** (P8, on the frozen
  finalist, after freezing — 91.67%).
- Scorer: upstream `evaluate.py` / `sb.py` only (immutable; LibreOffice
  headless recalculation, `transform_value` normalization, judges' `--all`
  mode). No custom scorer anywhere.
- Golden isolation: goldens readable only by evaluation and TRAIN-side reward
  construction; enforced by `research/tests/test_golden_isolation.py` and
  `research/experiments/audit_traces.py`. E009 and E015 trace audits: CLEAN
  (structure, coverage, no lookup smell, no golden values in prompts).
- Sacred-400: full-400 runs are single measurements of frozen configs, never
  a tuning loop (E009, E015 only).
- Nondeterminism: temperature-0 sampling still flips ±3–4 tasks/run
  (measured on byte-identical prompts in E007); replay/matched-control used
  for attribution.

## 6. Reproduction

```sh
# build (repo root)
docker build -t superspreadsheets .
# run (reads /data read-only, writes /out; unattended)
docker run --rm -e TINKER_API_KEY -e TINKER_PROJECT_ID \
    -v <dataset dir>:/data:ro -v <empty dir>:/out superspreadsheets
# env vars: TINKER_API_KEY, TINKER_PROJECT_ID (hackathon key's default
# project is read-only; team project id required). Never committed.
# local inference (finalist config):
cd research && uv run inference/cascade_predict.py --out-dir <out> \
  --base-model Qwen/Qwen3.8-27B --ids <ids> --concurrency 6 \
  --max-tokens 24576 --escalation-max-tokens 32768
# official evaluation:
uv run evaluate.py --predictions <predictions.jsonl> --all --out results.json
```
Final cold retest of the container on a goldenless dataset copy: PASS,
2026-09-06 09:03 (`OVERNIGHT_STATE.json` → morning.docker_retest).

## 7. Repository map (judge-relevant)

| Path | Purpose |
|---|---|
| `results.json`, `predictions.jsonl`, `outputs/`, `traces/`, `run.log` | the E015 submission run artifacts (contract layout) |
| `SUBMISSION.md` | submission form content |
| `EXPERIMENTS.md` | full ablation log incl. negatives, transition counts |
| `docs/RESEARCH_APPENDIX.md` | judge-facing research narrative |
| `docs/E009_RESIDUAL_AUDIT.md`, `docs/RESIDUAL_FRONTIER.md` | 95-failure classification, frontier analysis |
| `docs/H12_REWARD_ABLATION_PLAN.md`, `docs/H13_ONLINE_RLVR_PLAN.md`, `docs/H13C_FULLTRAIN_PLAN.md` | frozen preregistrations |
| `research/inference/` | the h8 cascade (serialize/health/invariants/cascade/write/parse) |
| `research/baseline/` | untouched starter (measured reference) |
| `research/experiments/` | runner, compare (4-bucket diffs), replay, classify, trace audit |
| `research/training/` | rollout/curate/sft2/pg_train/h13 envs + launchers |
| `research/tests/` | golden-isolation, sheet-aware write, reward-agreement, trajectory-integrity |
| `research/splits/` | frozen splits + canary24 |
| `experiments/<id>/` | per-run manifests (git commit, command, params) + official results.json |
| `Dockerfile` | judges' contract container |
| `MORNING_REPORT.md`, `OVERNIGHT_STATE.json`, `RESUME_AFTER_COMMUTE.md` | campaign state machine + continuity |

## 8. Negative results (exact cause → result)

- **E006 formulas everywhere**: +3 never-solved conversions, −8 regressions
  (wrong formulas where literals already passed) → policy rejected; became
  the gated escalation design.
- **E014 H4 best-of-N**: net −3 on dev; mechanism: trio candidates sampled
  with the champion prompt outvoted the sighted escalation artifact on
  view-doomed tasks (15671, 54590); route-matched H4C fix registered, unrun.
- **P-patch targeted repair**: 0 conversions, 1 allowlisted regression
  (496-34); consensus-wrong answers defeat golden-free triggers.
- **E012 first RSFT**: dev 78.3 → 41.7–46.7 across 3 variants; root cause
  thinking-stripped SFT targets (median 253 tokens vs thousands); narrowed
  claim: "RSFT on thinking-stripped targets fails" — corrected pipeline
  (F0 gate) eliminated the collapse but plasticity = control.
- **H12 reward ablation**: R0/R1/R2 all safe, none above control; discrete
  R1 offline-predicted under-informative (gradient-dead groups) and measured
  no better.

## 9. Claim audit

**MEASURED** (safe to state as results): every number in §1; §3 table; §4
canary rows for completed arms; trace audits CLEAN; Docker cold retest PASS;
E009→E015 transitions 22/15/+7; local_test 91.67% single-touch; ±3–4 noise
floor; zero sentinel regressions across all 7 trained variants.

**INFERRED** (state as interpretation, not measurement): mechanism
attribution of the 22 E015 fixes to specific harness changes (supported by
task-id overlap with train probes, but the 400-run is one sample);
"cell_accuracy 0.386 is whale-dominated" (9 tasks hold ~87% of graded cells —
the count is measured, the *dominance* framing is interpretation);
"truncation class shrank because of the 32k rung" (counts measured 28→22,
attribution inferred); "post-training is safe-but-neutral at these budgets"
(true of all completed arms; generalisation beyond them is inference).

**IN-FLIGHT** (must not appear as results): H13A final checkpoint + canary;
H13C training/canary/any coverage claim (state 269/280 sampleable + 11
excluded if mentioned); any dev60/promotion outcome; any claim that online
RLVR does/doesn't help — only step-8-neutral is measured.
