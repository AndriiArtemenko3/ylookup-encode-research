# Experiment map — decoder and lineage

Internal experiment IDs are append-only and were never renamed (renaming
would break manifests, logs and diffs). This document decodes them.

## ID prefixes

- **E** — primary measured experiment/run (official scorer, frozen config).
- **H** — hypothesis/mechanism branch, usually preregistered in `docs/H*_PLAN.md` before execution. An H-branch that survives becomes part of a later E-run.
- **P** — probe or supporting confirmation measurement (small n, mechanism evidence, or a single-use split confirmation).
- **C24 / canary** — the frozen 24-task safety canary: 12 *sentinels* (tasks the base system reliably passes; any regression = capability damage) + 12 *opportunity* tasks (near-misses; base control passes 2/12). Used to evaluate trained checkpoints cheaply and safely.
- **F\*** — training-data / trajectory-pipeline phases (rollout capture, curation, trajectory-integrity gating). `F1v2-*` directories are the corrected reasoning-preserved pipeline.
- Honest inconsistency note: numbering is chronological-ish but not gapless (E005, E010, E011 were folded into neighbours or never promoted from plans); H-numbers do not imply order of adoption.

## Lineage — the weekend in six phases

**Phase 0 — establish the baseline.**
`E001` untouched starter on dev (n=60): **46.7%**. Diagnosis: 24/32 failures were token-cap truncations. → motivated Phase 1.

**Phase 1 — remove runtime/representation failures (dev, n=60).**
`E002` budget 8k→24k: **61.7%** (+9/−0). `E003` typed Excel date/time writes, replay-validated at zero token cost: **76.7%** (+9/−0). `E004` salvage parser + merged-cell unmerge: **78.3%** (+1/−0). → wrong-values became the dominant failure; visibility/formula hypotheses next.

**Phase 2 — formula/context policy (dev, n=60).**
`E006` formulas everywhere: **70.0%** (+3/−8, **negative** — capability real, policy wrong). `E007` coverage serialization alone: **71.7%** (+1/−5, **negative** — measured the ±3–4-task sampling-noise floor on byte-identical prompts). `E008` the evidence-gated cascade built from both negatives: **83.3%** (+3/−0). → the champion architecture.

**Phase 3 — full-benchmark reality check.**
`E009` first frozen full-400 measurement of the champion: **76.25% (305/400)**. Residual audit of all 95 failures (`docs/E009_RESIDUAL_AUDIT.md`) found: 53 healthy-but-wrong, a 28-task truncation class, multi-sheet addressing bugs, whale-task cell-accuracy skew. → motivated Phase 4 mechanisms.

**Phase 4 — residual-tail mechanisms (train probes + dev, n=60).**
`H3` structural invariants + guarded repair (train probe: 3/6 hard conversions, 0 control regressions) and the multi-sheet addressing fix (2 deterministic train conversions) → `E013` dev: **85.0%** (+2/−1) — the finalist. `H4`/`E014` risk-gated best-of-N: **80.0%** (+1/−4, **negative** — blind candidates outvote sighted artifacts); `H4B` execution-backed selection: offline-identical to H4, redundant; `P-patch` targeted repair: 0 conversions/1 regression, **negative**.

**Phase 5 — final measurement.**
`P8` one-touch local_test confirmation of the frozen finalist (n=60): **91.67% (55/60)**. `E015` final frozen full-400: **78.0% (312/400)**, +22/−15 vs E009 — the submission run.

**Phase 6 — post-training (all Qwen3.8-27B + LoRA rank 32; canary = C24 above).**
`E012` first RSFT: dev collapse ~30pts; root cause thinking-stripped targets (median 253 tokens) → the F0 trajectory-integrity gate. Corrected RSFT (253 examples, lr 1e-5/2e-5): safe, opportunity = control. `H12` reward ablation (REINFORCE, 56-group frozen band; R0 continuous / R1 discrete / R2 hybrid): 13/13/14 of 24 — safe, none above control. `H13B` hard-mined expert iteration (100 frozen examples): 13/24 — safe, one below control. `H13A` true online RLVR (51 boundary groups, K=8, 20 updates): step-8 canary neutral (= control); final-checkpoint evaluation pending at submission. `H13C` full-train online RLVR (269/280 sampleable tasks, 11 unsampleable whales excluded and listed, K=4, 14 updates, 1,120 fresh episodes): trained to full coverage; evaluation pending at submission.

Cross-phase constant: every accepted mechanism is golden-free and
task-ID-free; every negative is preserved in `EXPERIMENTS.md` with its
transition counts.
