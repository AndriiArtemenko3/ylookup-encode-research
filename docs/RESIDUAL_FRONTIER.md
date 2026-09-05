# Residual Frontier — Evidence-First Mining of the E009 Tail (95 failures)

Analysis-side only (goldens via official results; train rollout pools for the
capability/selection axis). MEASURED vs INFERRED vs PROJECTED separated.

## Capability-vs-selection axis (MEASURED on the 75 tail tasks with train pools)

| Label | n | Meaning |
|---|---|---|
| **SELECTION-LIMITED** | **22** | a fully correct candidate already exists in best-of-4 @0.7 |
| NEAR-CAPABILITY | 12 | no pass in pool, best candidate ≥0.70 cell-accuracy |
| CAPABILITY-LIMITED | 41 | pool never gets close |
| (no pool: dev/local_test tail) | 20 | axis not measurable without extra sampling |

Direct answer to Q1: **≥22 of the 53 healthy-but-wrong residuals are
measured selection-limited** — the model already solves them; serving throws
the solution away. (INFERRED scaling to the unmeasured 20: ~28 total.)

## Mutually exclusive primary view (no double counting; priority: bug > truncation > measured-selection > mechanism)

| Primary class | n | Active mechanism | Evidence |
|---|---|---|---|
| **truncated at 24k escalation cap** | **28** | h7/h8 already raised escalation budget to 32k — merged, rides into any h8 candidate | E009 ran h6 (24k); MEASURED cap-hits in selected traces |
| **selection-limited (measured)** | 18 | H4 risk-gated selector (E014 dev running tonight) | train pools + offline selector +3.4pp |
| incomplete output | 14 | patch repair / H3 completeness | probe in flight |
| unknown | 11 | — | needs trace reading |
| wrong lookup/range | 7 | H4 / post-training | |
| arithmetic/logic | 6 | post-training | |
| **multi-sheet coordinate bug** | **5** | deterministic fix merged in h8 | unit-tested; train probe in flight |
| formula error | 4 | H3 | E013 evidence |
| missing visibility | 2 | inspection tools | |

## Overlapping addressability view (tags, not additive)
post-training 46 · targeted repair 38 · code execution 25 · selection 22
(measured) + up-to-28 (inferred) · truncation-budget 28 · msheet 5.

## Mechanism cards — the two chunky classes

**CLASS: truncation@24k (28 tasks, 29% of tail).** Observable: selected trace
`output_tokens == 24576`. Cause: h6's escalation budget. Fix already merged
(32k). Reachable subset: E002→E003 history says extra budget converts ~40–60%
of truncations when content fits; PROJECTED net +8–14. Regression channel:
none new (same strategy, bigger budget). Falsification: any h8-based full-400
run measures it directly. Two evidence sources: measured cap-hits + prior
budget-ablation (E002) conversion behaviour.

**CLASS: selection-limited (18–28 tasks).** Observable: risk-gated task where
pool contains a healthy candidate disagreeing with the artifact. Mechanism:
H4 frozen selector. Reachable: offline selector recovered 54% of oracle gap on
train; PROJECTED net +6–12 with adoption-precision risk. Falsification:
E014 (running). Two sources: measured pools + offline selection result.

## High-value questions (G)

1. Selection-limited among healthy-but-wrong: **22 measured** (see above).
2. ≤5-cell residuals with golden-free trigger signals available: 20/26 have
   train pools (disagreement computable); patch probe tests trigger→fix live.
3. Large-output/combinatorial: 28 are budget-truncations (representation);
   the whale subset (9) is execution-representation (H10 probing now).
4. Incomplete-output recoverable by continuation/budget: subsumed mostly by
   the 32k class; remainder 14 needs patch/H3, not a new solver.
5. Deterministic bug/type residuals: **5 msheet (measured)** + 2 visibility.
6. Genuinely capability-limited after pool/harness analysis: **41 measured on
   train-overlap; INFERRED ~50–55 of 95 overall** — the honest hard core.
7. Largest mutually-exclusive class with generic intervention + train
   evidence: truncation@24k (28) — mechanism already merged.

## Overlap-adjusted projection from 305/400 (PROJECTED, ranges)

| Source | Conservative | Likely |
|---|---|---|
| truncation@24k (32k budget, in h8) | +6 | +10 |
| selection (H4, if E014 GREEN) | +4 | +8 |
| msheet fix | +2 | +3 |
| H3 repair (dev-confirmed +1/60) | +2 | +4 |
| patch/incomplete | +1 | +3 |
| **Total** | **+15 → 320/400 = 80.0%** | **+28 → 333/400 = 83.25%** |

**Path assessment: 85% (340/400) is the stretch ceiling of current evidence;
87.5% and 90% are NOT supported** — the measured capability-limited core
(~50 tasks) blocks them without a genuinely new capability mechanism.

## New-mechanism verdict (per amendment §I/§J)

**No new mechanism launched.** The mining found the tail's chunky classes
already covered by active, evidence-backed mechanisms (32k budget, H4, msheet
fix, H3/patch). Launching a novel mechanism tonight would duplicate coverage
rather than extend it — recorded as the evidence-first conclusion.
