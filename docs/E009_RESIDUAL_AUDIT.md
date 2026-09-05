# E009 Residual Audit — the 95 official-400 failures

Method: `research/experiments/residual_audit.py` (analysis-side; goldens via
official results only). Full per-task rows: `experiments/E009-residual-audit.json`.

## Headline aggregates

| Metric | Count | Share of failures |
|---|---|---|
| **A. HEALTHY-BUT-WRONG** (passed every health check, still failed) | **53** | 56% |
| B. ≤5 wrong cells | 26 | 27% |
| C. ≥90% cell accuracy | 16 | 17% |
| D. Large sheet-level transformations (>300 answer cells) | 22 | 23% |

A is the architectural finding: `health.py` detects distress, not semantic
wrongness — over half the residual failures sail through it. This is H9's
target population.

## By failure scale
broad 26 · partial 36 · dead 13 · sparse 11 · 1-cell 9

## By dominant mechanism (heuristic classification)

| Mechanism | n | Primary candidate intervention |
|---|---|---|
| large-output / combinatorial | 26 | code execution (H10) |
| incomplete output | 17 | targeted/structural repair (H3) |
| unknown | 15 | needs trace reading / post-training |
| arithmetic & logic | 12 | post-training / self-consistency |
| wrong lookup/range | 12 | self-consistency (H9) / post-training |
| formula error | 6 | repair (H3) |
| multi-sheet reasoning | 5 | **partly the coordinate-collision BUG (Task 7A)** |
| missing source visibility | 2 | inspection tooling |

## By selected cascade stage
champion 45 · formula 33 · repair 17 (escalation fires but doesn't always save)

## E. Addressability (tags overlap)
post-training 46 · targeted repair 38 · code execution 25 · self-consistency 11 · inspection 2

## Task 7 robustness audits

- **7A multi-sheet coordinate collision — CONFIRMED BUG.** 5 public tasks
  (283-32, 156-14, 170-13, 141-20, 302-1) have answer ranges spanning sheets
  with overlapping coordinates; `write_output` keys cells by coordinate only,
  so one sheet's values overwrite all. Train evidence: 156-14 and 170-13 fail
  with 100%-stable residuals — the bug's signature, previously misread as
  capability. Fix: sheet-qualified cell addresses in the answer schema +
  (sheet, coord) keying; prompt mentions sheet-qualification only for
  multi-sheet tasks. Regression risk: low (single-sheet path unchanged);
  needs matched-control validation. Holdout rationale: real fund books are
  multi-sheet by nature.
- **7B same-prompt 32k retry on champion truncation**: mechanism exists
  (escalation budget), but a same-strategy retry before strategy switch is
  cheap and preserves champion behaviour; evidence: 26 large-output failures.
- **7C patch repair (regenerate only K suspicious cells)**: supported by
  B=26 (≤5 wrong cells); pairs naturally with H9 disagreement flags.
- **7D formula static whitelist too strict**: prefer recalculation evidence
  over unknown-function rejection; current static check only *flags* (repair
  prompt), never rejects outright — risk is wasted repairs, keep but monitor.
