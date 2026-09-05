# E002 failure taxonomy — all 23 failed dev tasks classified

Method: `research/experiments/diagnose.py` builds one evidence bundle per
failed task (trace error + token counts, official expected-vs-actual
mismatches from results.json, sheet dimensions vs the 120x30 serialisation
window, reply tails). Each task was then classified by its primary blocking
cause. Golden-derived values appear here via the official evaluator's output
only — analysis side, never inference.

## Issue table, sorted by frequency

| # | Pattern | Tasks | Ids | Primary evidence | Candidate fix |
|---|---------|-------|-----|------------------|---------------|
| 1 | **Date/time computed correctly but written as TEXT, golden holds real datetime/time** | **9** | 177-6, 250-20, 333-29, 343-20, 35739, 388-47, 567-21, 58942, 66-24 | Mismatches read "expected '2014-02-05 00:00:00' got '2014-02-05 00:00:00'" — identical strings; golden is a datetime object, ours a str. Exactly the README's "dates must be real dates, not text" trap. All 9 pass every non-date cell. | Harness: in `write_output`, coerce strings matching strict ISO datetime/time patterns to `datetime`/`time` objects before writing. No prompt/model change. |
| 2 | **Required data outside the 120x30 serialisation window** | **7** | 15671, 486-17, 49667, 50193, 51090, 54590, 6698 | 15671 answers B1:B260, nulls start exactly at B121 (the window edge). 54590 needs columns GK/GO/GR (cols 193+, window shows 30) → returned 0. 6698 aggregates 9493 rows → wrong counts. 4 of these also burn to the token cap reasoning about data they cannot see. | Serialisation strategy: include answer-range rows/cols and referenced ranges; or targeted range reads / code execution. Design experiment, not a one-liner. |
| 3 | **Output too large or combinatorial reasoning → still truncated at 24k** | **4** | 254-34, 290-27, 433-47, 524-31 | 290-27 must emit 1116 cells. 254-34 is a subset-sum puzzle (find values summing to 994108–994112) — model reasons forever. Raising the cap again is not the answer. | Cheaper output formats (formulas / code instead of literal values); possibly lower reasoning effort. Harness evolution track. |
| 4 | **Genuine logic/format interpretation errors** | **2** | 32438, 51680 | 32438: emitted '06:08:00 PM', golden wants '18:08:00'. 51680: normalised 'Green ,' (trailing space in source header) to 'Green,' — cleaned data it should have copied verbatim. | Prompt guidance on format fidelity; low priority at n=2. |
| 5 | **Baseline bug: MergedCell write crash** | **1** | 38703 | `AttributeError: 'MergedCell' object attribute 'value' is read-only` — task asks to unmerge first; `write_output` writes into a merged range and dies. | Harness: unmerge cells overlapping the answer range before writing. Deterministic +1. |

## Reading

- Patterns 1 + 5 are **write-side representation bugs, not model failures**:
  the model already solved 10 of 23 failed tasks. Fixing how we write its
  answers is worth up to +10 tasks (dev 61.7% → ~78%) with zero model risk.
- Pattern 2 (7 tasks) is the **serialisation/visibility problem** — the model
  cannot answer about data it never saw. This is the first structural harness
  experiment.
- Pattern 3 (4 tasks) motivates the **formulas/code output format** track.
- Estimates assume the shown mismatches are exhaustive per task (results.json
  lists max 5); the correct/cells counts are consistent with that, but the
  probe run after each fix is the real test.
