# Overnight Campaign Log — 2026-09-06 (pre-overnight ref: 59831a0)

Strategy: HARNESS_FIRST_OVERNIGHT. E009 (76.25% full-400) immutable fallback;
E013 (85.0% dev) best measured. Gates per overnight directive.

| Phase | Experiment | State | Verdict |
|---|---|---|---|
| 0 | preflight | done (oracle recheck backgrounded) | GREEN |
| 1 | P-msheet train probe (283-32,156-14,170-13) | pending | |
| 2 | E014 H4 risk-gated selector dev | pending | |
| 2B | H4B exec-evidence selector (train sim) | done | YELLOW — redundant with H4 on values-only pools (82.2=82.2); no dev run per gate |
| 3 | P-h10 train probe | pending | |
| 4 | P-patch train probe | pending | |
| 5 | RSFT lr2e-5 + canary | pending | |
| 7 | combined candidate dev | pending | |
| 8 | local_test single confirmation | pending | |
| 9 | full-400 (gated) | pending | |
| 10 | packaging | pending | |
