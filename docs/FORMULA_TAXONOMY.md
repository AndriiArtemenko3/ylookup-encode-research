# Formula taxonomy — train split (280 tasks)

Mined by `research/training/formula_analysis.py`. dev/local_test never opened.


## Golden answers

- workbooks containing formulas: 151 (by type: {'Sheet': 12, 'Cell-': 139})
- total formulas: 28850, mean length 49.8 chars, cross-sheet refs: 3428
- modern (_xlfn tier) usage: none

| Function | Count |
|---|---|
| IF | 7689 |
| LEN | 4487 |
| RIGHT | 4482 |
| INDEX | 4462 |
| COUNTIF | 4422 |
| MATCH | 4249 |
| AND | 3239 |
| SUM | 2574 |
| IFERROR | 2516 |
| TRIM | 1455 |
| MAX | 1078 |
| ROUNDDOWN | 1046 |
| VLOOKUP | 1014 |
| EOMONTH | 972 |
| MOD | 960 |
| YEARFRAC | 876 |
| LARGE | 776 |
| EDATE | 509 |
| DATEDIF | 493 |
| MIN | 468 |
| COUNT | 434 |
| ROW | 431 |
| CEILING | 321 |
| SUMPRODUCT | 232 |
| AVERAGEIFS | 224 |

| Co-occurrence | Count |
|---|---|
| LEN+RIGHT | 4459 |
| INDEX+MATCH | 4064 |
| AND+IF | 3239 |
| INDEX+TRIM | 1417 |
| MATCH+TRIM | 1417 |
| IF+SUM | 1079 |
| IF+ROUNDDOWN | 1046 |
| EOMONTH+MOD | 960 |
| IFERROR+LARGE | 749 |
| AND+ROUNDDOWN | 704 |
| AND+SUM | 704 |
| ROUNDDOWN+SUM | 704 |

## Input workbooks

- workbooks containing formulas: 105 (by type: {'Sheet': 15, 'Cell-': 90})
- total formulas: 18609, mean length 48.0 chars, cross-sheet refs: 1606
- modern (_xlfn tier) usage: none

| Function | Count |
|---|---|
| IF | 6840 |
| COUNTIF | 4361 |
| AND | 3118 |
| IFERROR | 2239 |
| SUM | 2085 |
| ROUNDDOWN | 1046 |
| MAX | 1011 |
| LARGE | 776 |
| VLOOKUP | 768 |
| MATCH | 690 |
| INDEX | 661 |
| MOD | 482 |
| DATEDIF | 480 |
| EOMONTH | 480 |
| COUNT | 434 |
| ROW | 391 |
| MIN | 388 |
| CEILING | 321 |
| ROUND | 166 |
| ROWS | 142 |
| OR | 128 |
| SUMPRODUCT | 79 |
| CONCATENATE | 70 |
| TODAY | 59 |
| TEXT | 51 |

| Co-occurrence | Count |
|---|---|
| AND+IF | 3118 |
| IF+ROUNDDOWN | 1046 |
| IFERROR+LARGE | 749 |
| IF+SUM | 705 |
| AND+ROUNDDOWN | 704 |
| AND+SUM | 704 |
| ROUNDDOWN+SUM | 704 |
| INDEX+MATCH | 661 |
| IF+MAX | 622 |
| AND+MAX | 614 |
| DATEDIF+EOMONTH | 480 |
| DATEDIF+IFERROR | 480 |
