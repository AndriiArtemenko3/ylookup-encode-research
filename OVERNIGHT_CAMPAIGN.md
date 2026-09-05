# Overnight Campaign Log — 2026-09-06 (pre-overnight ref: 59831a0)

Strategy: HARNESS_FIRST_OVERNIGHT. E009 (76.25% full-400) immutable fallback;
E013 (85.0% dev) best measured. Gates per overnight directive.

| Phase | Experiment | State | Verdict |
|---|---|---|---|
| 0 | preflight | done (oracle recheck backgrounded) | GREEN |
| 1 | P-msheet train probe | done | GREEN — 156-14 156/156 & 283-32 28/28 (bug-signature tasks fixed); 170-13 content-bound as expected; IN candidate |
| 2 | E014 H4 risk-gated selector dev | pending | |
| 2B | H4B exec-evidence selector (train sim) | done | YELLOW — redundant with H4 on values-only pools (82.2=82.2); no dev run per gate |
| 3 | P-h10 train probe | pending | |
| 4 | P-patch train probe | done | RED/YELLOW — 0 conversions, 1 allowlisted regression (496-34), consensus-wrong defeats triggers; EXCLUDED from candidate |
| 5 | RSFT lr2e-5 + canary | done | YELLOW — 12/12 retention, plasticity=control, NLL flat; LR escalation STOPPED per gate; RLVR condition unmet |
| 7 | combined candidate dev | pending | |
| 8 | local_test single confirmation | pending | |
| 9 | full-400 (gated) | pending | |
| 10 | packaging | pending | |
