# H4B — Executable-Evidence Selector (Preregistered, FROZEN)

Frozen BEFORE any H4 dev outcome exists (E014 not yet launched at freeze
time) and before any H4B result. Separate experiment from H4; H4's frozen
spec and result are not reinterpreted.

## Hypothesis
Deterministic, golden-free executable verification of candidate workbooks
recovers part of the residual selection headroom (train: H4 selected 82.2%
vs candidate-pool oracle 85.3%) by demoting plausible-but-broken candidates
(error values, incomplete coverage, unstable round-trips) that lexical/health
signals rank too high — targeting the healthy-but-wrong class (53/95 of E009
residual failures).

## Candidate pool
Identical to H4: cascade artifact + 3 temp-0.7 champion samples. **Dev
confirmation reuses the exact candidates stored in E014's traces/artifacts —
zero new sampling.** No N search.

## FROZEN feature set and lexicographic order (highest first)
1. **exec_ok**: workbook written without exception AND, after LibreOffice
   recalculation of the candidate itself, target cells contain zero explicit
   error values (#REF!, #VALUE!, #NAME?, #N/A, #DIV/0!, #NULL!, #NUM!). For
   candidates with no formulas, recalculation is skipped and error strings
   are checked directly (recalc cannot change literal values).
2. **coverage**: fraction of expected answer coordinates represented in the
   candidate's parsed answer, bucketed {1.0, [0.9,1.0), <0.9}. Cells the
   candidate explicitly nulls COUNT as represented (a legitimate empty is a
   decision, not an omission) — this avoids the H3 emptiness-fill loophole.
3. **round_trip_stable**: save → recalc → reopen leaves target literal values
   unchanged (formula cells compare recalculated value to itself once —
   instability = negative evidence). Values-only candidates are stable by
   construction.
4. **strict parse** then **closed/non-truncated**.
5. **agreement**: mean pairwise cell agreement across the pool (canonicalised
   per official-style normalisation, no goldens).
6. **answered count**, then pool index (cascade artifact first).
Ties at every level resolve toward the cascade artifact (conservative
selector; champion always in pool).

## TRAIN mechanism test (before any dev)
Offline over existing F1-rollouts candidate pools (no new sampling): report
pass@1, H4 selected, H4B selected, oracle, headroom fraction recovered,
adoptions, adoption precision, regressions vs H4, runtime. GREEN = H4B >
H4 by a meaningful margin without a new regression mechanism; the target
diagnostic is cases where a correct candidate existed, H4 chose wrongly, and
executable evidence corrects the choice.

## Dev confirmation (only if TRAIN GREEN)
Exactly one run: re-select over E014's stored pools; score with the official
evaluator as E014B. Compare vs E013 and frozen-H4 (E014). No selector edits
after seeing dev. Full-400 gains are NOT presumed; +3.4pp train ≈ ~13 tasks
per 400 only under perfect generalisation — an estimate, not a claim.
