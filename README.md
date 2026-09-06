# Superspreadsheets

### Improving spreadsheet reliability with failure-driven, generalization-oriented systems design.

Built solo for the **Ylookup × Encode AI Hackathon — Research Track** (5–6 September 2026).

Given an Excel workbook and a natural-language instruction, the system must return the modified workbook. A task passes only when **every graded cell is correct after LibreOffice recalculation** — one wrong cell fails the task. The required model is `Qwen/Qwen3.8-27B`, and we kept it untouched in the submitted configuration. We treated the weekend as an ML-systems reliability problem rather than prompt tuning:

> measure failures → identify the mechanism → change one thing → evaluate → keep only what survives.

## Results

| Evaluation | Exact task pass rate |
|---|---:|
| Organizer one-shot reference (organizer-advertised, not re-measured by us) | 59.0% |
| **Our final public 400-task run (E015)** | **78.0% — 312/400** |
| Fixed dev split (n=60) | 85.0% — 51/60 |
| Held-out local test, touched exactly once (n=60) | 91.67% — 55/60 |

These are **different evaluation sets, not repeated measurements of the same sample** — the 91.67% is our internal held-out split, not a public-benchmark figure.

Final full-400 detail: **312/400 exact pass**, cell-level task pass 83.64%, sheet-level task pass 65.6%, items/graded/missing/errors = 400/400/0/0 ([results.json](results.json)). Against our earlier full-400 champion (E009, 76.25%), the finalist produced **22 FAIL→PASS and 15 PASS→FAIL transitions, net +7 tasks** — and the fixed tasks fall in exactly the failure classes the added mechanisms target.

## Research goal: improve reliability, not just benchmark fit

The core question we set out to test:

> Can a relatively small model become more reliable at spreadsheet work through mechanisms that should transfer to workbooks and instructions outside the specific public benchmark tasks?

We deliberately did not optimize around task IDs or golden-answer-specific patches. Every accepted change is a generic model-runtime or spreadsheet-semantics mechanism, and the evaluation was structured to preserve evidence that the system works on data not used for iteration.

## Why the improvements should transfer

**Protected held-out data.** The 400 public tasks were frozen into 280 train / 60 dev / 60 local_test (seed 42, checksum-guarded). All iteration ran on train and dev. local_test was touched **exactly once**, only after the finalist was frozen, and scored 91.67%. This provides evidence that the finalist was not merely tuned to the dev set — it is not proof of arbitrary out-of-distribution generalization.

**The public 400 as measurement, not tuning loop.** Full-400 runs (E009, then E015) were single measurements of frozen configurations. Post-hoc failure analysis informed *hypotheses*, which were then developed on train and validated on dev before any refrozen configuration was measured again.

**Generic mechanisms instead of task-specific fixes.** Each accepted mechanism encodes spreadsheet or model-runtime semantics that hold regardless of benchmark identity: typed date/time cells (Excel semantics), sheet-qualified addressing (real workbooks reuse coordinates across sheets), merged-cell-safe writing, recalculating **our own output** to detect formula errors, conditional context expansion (any large workbook can hide relevant cells outside a fixed serialization window), truncation detection with token escalation (an output-budget property of the model system), structural completeness/type invariants, and conservative artifact selection that never replaces a known-good path without evidence. None of these read task IDs or golden values.

**Rejected brittle improvements.** Generalization discipline also meant rejecting local wins with high regression risk: formulas-everywhere converted 3 never-solved tasks but regressed 8; best-of-N selection let blind candidates outvote a sighted artifact; patch repair lost to consensus-wrong outputs. We preferred mechanisms with a clear causal model and low regression surface over locally attractive score changes.

**Evaluation ladder.**

```text
TRAIN (280)      mechanism discovery, reward construction
   ↓
DEV (60)         controlled one-change-at-a-time validation
   ↓
LOCAL_TEST (60)  untouched until finalist freeze, single confirmation
   ↓
PUBLIC 400       frozen measurement (E009, E015)
   ↓
PRIVATE HOLDOUT  judge-run unseen spreadsheets — the strongest external test
```

We do not know the private-holdout result; the ladder is designed so that it should not be a surprise.

## The system

The final system is a conservative inference cascade around Qwen3.8-27B that spends extra compute only when there is golden-free evidence that the ordinary path is failing.

```text
workbook + instruction
        │
        ▼
┌─────────────────────────┐
│ Qwen3.8-27B             │
│ values-first solve      │
│ 24,576 token budget     │
└────────────┬────────────┘
             │
             ▼
      golden-free checks
             │
       ┌─────┴─────┐
       │           │
    healthy     distressed /
       │        view-doomed
       │           │
       │           ▼
       │   expanded workbook view
       │   formula-capable solve
       │   32,768 token budget
       │           │
       │     evidence-fed repair
       │           │
       └─────┬─────┘
             ▼
      structural invariants
             │
             ▼
       artifact selection
             │
             ▼
 typed + sheet-aware writer
             │
             ▼
   LibreOffice recalculation
             │
             ▼
        final workbook
```

In execution order: a **values-first champion attempt** (baseline 120×30 serialization, 24,576 tokens), skipped only on provable unwinnability (answer range over 300 cells, or answer cells outside the serialized view); **golden-free health checks** on our own artifact — truncation, parse damage, static formula issues, Excel error values after recalculating our own output; **gated escalation** to an expanded coverage serializer with formula-visible cells and a formula-permitting prompt at 32,768 tokens, followed by one **evidence-fed repair** quoting the concrete defect list; **structural invariants** (requested-range completeness, column-type consistency) triggering at most one repair whose writes are restricted to a **changed-cell allowlist**; **conservative selection** of the healthiest artifact with ties to the champion, so the per-task worst case is the champion's own output; and a **writer** that produces typed ISO dates/times, prefixes modern functions for LibreOffice, unmerges target ranges before writing, and uses **sheet-qualified addresses** whenever the answer range spans sheets.

## The ablation journey (dev split, n=60)

| Exp | One change | Dev pass | Flips | Verdict |
|---|---|---:|---|---|
| E001 | untouched starter | 46.7% | — | measured floor |
| E002 | token budget 8k → 24k | 61.7% | +9 / −0 | adopted |
| E003 | typed Excel writes (dates as dates) | 76.7% | +9 / −0 | adopted |
| E004 | salvage parser + unmerge | 78.3% | +1 / −0 | adopted |
| E006 | formulas everywhere | 70.0% | +3 / −8 | **negative** |
| E008 | evidence cascade | 83.3% | +3 / −0 | adopted |
| E013 | structural repair + multi-sheet | 85.0% | +2 / −1 | adopted → finalist |
| E014 | risk-gated best-of-N | 80.0% | +1 / −4 | **negative** |
| E015 | frozen finalist on the **full 400** (different split) | **78.0%** | 22 / 15 vs E009 | submission run |

A few simple mechanisms produced most of the gain; later mechanisms showed diminishing returns; the negative experiments materially shaped the final architecture.

**Three findings worth keeping:**

1. **Token budget.** At the 8k starter budget, truncation dominated failures; raising it to 24k fixed 9 dev tasks with zero regressions. Some apparent reasoning failures were incomplete-output failures.
2. **Spreadsheet representation.** Writing dates as typed cells fixed 9 more dev tasks — validated by replaying stored responses through the new write path at **zero additional model calls**. Deterministic spreadsheet semantics belong in the harness, not necessarily in model weights.
3. **More freedom can hurt.** Unrestricted formula use converted 3 never-solved tasks and regressed 8. The capability existed; the policy was wrong. This negative result is why formula mode is gated on evidence rather than universal.

## Negative results

Kept deliberately, because they reduced uncertainty and shaped the system: **E006** formulas everywhere (+3/−8, rejected); **E014** best-of-N selection (net −3: candidates sampled with the champion prompt outvoted the sighted escalation artifact on view-doomed tasks); **patch repair** (0 conversions, 1 regression — consensus-wrong answers defeat golden-free triggers); **E012** first RSFT attempt (dev collapsed ~30 points across three variants; forensics traced it to thinking-stripped SFT targets — median 253 tokens against successful trajectories of thousands); **corrected RSFT** (collapse eliminated, plasticity ≈ control); **H12 reward ablation** (continuous/discrete/hybrid rewards all safe, none above control).

## Post-training: investigated seriously, reported by what it measured

Sequence, with precise terminology — LoRA is the parameter-efficient update mechanism (rank 32 throughout); SFT is an imitation objective; RLVR is verifier-grounded outcome optimization:

1. rejection-sampling SFT on verifier-approved trajectories (E012 — collapsed; root cause was data representation, not RSFT);
2. a trajectory-integrity gate (exact prompt+completion token capture, reasoning preserved, length-regime guard), then corrected RSFT at two learning rates;
3. a reward-function ablation (H12: continuous R0, discrete R1, hybrid R2) via on-policy REINFORCE;
4. hard-mined expert iteration (H13B, 100 frozen examples);
5. true online RLVR with fresh current-policy rollouts and importance-sampled updates on boundary tasks (H13A);
6. the same online RLVR over the full train distribution (H13C, 269/280 sampleable tasks — 11 whale workbooks whose serialized observations cannot fit any context are excluded and listed).

**Completed evidence at README freeze:** corrected RSFT — safe, control-level. H12 R0/R1/R2 — safe, none above control. H13B — safe, one opportunity task below control. Across every corrected arm, sentinel retention on the frozen canary was **12/12 — zero capability collapses** — so the trajectory-integrity fix demonstrably solved destructive training. But safe ≠ better: **no completed arm has produced a measured exact-pass improvement over the base+harness control**, and the submitted 78.0% is attributable to the harness, not post-training.

**H13A / H13C status:** both completed their frozen training budgets (20/20 and 14/14 updates) shortly before README freeze; H13A's mid-training canary was neutral (it passes exactly the control's opportunity tasks). Their **final-checkpoint evaluations had not yet run at freeze**, so no conclusion about online RLVR's end state is reported here.

## Evaluation and anti-overfit discipline

Fixed 280/60/60 split; local_test one-touch. Scoring is exclusively the upstream official evaluator (LibreOffice recalculation, judges' `--all` mode) — no custom scorer anywhere. Golden answers are readable only by evaluation and TRAIN-side reward construction, never by runtime inference — enforced by automated tests ([research/tests/](research/tests/)) and trace audits over both full-400 runs (clean: no golden content in any prompt, no task-ID lookups). Temperature-0 sampling still flips ±3–4 dev tasks between runs — measured on byte-identical prompts — so attribution used stored-response replay and matched controls rather than headline deltas.

## Reproduction

```sh
# build (repo root)
docker build -t superspreadsheets .

# run — reads /data read-only, writes /out, unattended
docker run --rm \
  -e TINKER_API_KEY \
  -e TINKER_PROJECT_ID \
  -v <dataset-dir>:/data:ro \
  -v <empty-output-dir>:/out \
  superspreadsheets
```

No credentials are committed; the two environment variables above are required (the hackathon key's default project is read-only — the team project id is needed). Final cold retest of the container on a golden-free dataset copy: **PASS** (2026-09-06).

```sh
# finalist local inference
cd research && uv run inference/cascade_predict.py --out-dir <out> \
  --base-model Qwen/Qwen3.8-27B --ids <ids> --concurrency 6 \
  --max-tokens 24576 --escalation-max-tokens 32768

# official evaluation
uv run evaluate.py --predictions <predictions.jsonl> --all --out results.json
```

## Repository guide

| Path | What it is |
|---|---|
| [results.json](results.json), [predictions.jsonl](predictions.jsonl), [outputs/](outputs/), [traces/](traces/), [run.log](run.log) | the E015 submission run — all 400 tasks graded, 0 missing, 0 evaluation errors |
| [SUBMISSION.md](SUBMISSION.md) | submission form content |
| [EXPERIMENTS.md](EXPERIMENTS.md) | the full ablation log, negatives included, with transition counts |
| [README_FACTS.md](README_FACTS.md) | source-of-truth fact pack behind this README, with claim audit |
| [docs/RESEARCH_APPENDIX.md](docs/RESEARCH_APPENDIX.md) | the research narrative in full |
| [docs/RESIDUAL_FRONTIER.md](docs/RESIDUAL_FRONTIER.md) | classification of what still fails and why |
| [research/inference/](research/inference/) | the cascade: serialization, health checks, invariants, writer |
| [research/training/](research/training/) | rollouts, curation, RSFT, REINFORCE, online-RLVR environments |
| [research/experiments/](research/experiments/) | runner, official-scorer diffing, replay, failure classification, trace audit |
| [research/tests/](research/tests/) | golden-isolation, sheet-aware-write, reward-agreement, trajectory-integrity guards |
| [research/splits/](research/splits/) | the frozen splits and canary |
| [Dockerfile](Dockerfile) | the judges' contract container |

## Takeaway

A large fraction of apparent model failures were actually failures of context allocation, spreadsheet representation, validation, or routing — and those can be measured and fixed without changing the underlying model. Post-training became reliably non-destructive once trajectory representation was fixed, but completed training runs had not yet produced a measured exact-pass improvement over the base+harness at README freeze. The final public result: **312/400 = 78.0%**, with a one-touch held-out local_test result of **55/60 = 91.67%**.
