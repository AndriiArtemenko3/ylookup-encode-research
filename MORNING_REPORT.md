# MORNING REPORT — Ylookup × Encode Overnight Campaign (2026-09-06)

Pre-overnight reference: 59831a0. All numbers below are measured unless
marked PROJECTED. [PENDING] sections fill as final runs land.

## Executive summary

- Best measured dev configuration: **E013 / h8 harness, base model — 85.0%**
  (51/60); adopted as the frozen finalist harness.
- Best full-400: **E015 78.0%** (312/400; sheet-level 65.6% vs E009's 60.0%)
  — the finalist's 32k-budget, multi-sheet, and H3 mechanisms delivered +7
  tasks over E009's 76.25%; truncation class shrank 28→22, date/merged-cell
  classes stay 0. Trace-audited CLEAN; now the submission run.
- Overnight candidate vs E013: no stacked candidate beat E013 — H4 selection
  went RED (net −3, mechanism attributed), patch repair RED, H4B redundant;
  E013's own config, already containing every GREEN mechanism, stands.
- Post-training: corrected-representation RSFT and three reward-ablation
  policy-gradient arms are uniformly **safe but behaviorally ~neutral** at
  conservative matched budgets — the E012 collapse is causally attributed to
  thinking-stripped targets, and reward substitution did **not** change that
  (R0 13/24, R1 13/24, R2 14/24 vs base control 14/24; all 12/12 sentinels —
  zero regressions, no arm above control).
- Adaptive compute: the 32k escalation rung (merged pre-overnight) is the
  single largest projected full-400 lever (28-task truncation class);
  H11's deeper 40k rung: probe killed by the macOS memory incident, never
  completed — registered unrun.
- New chunky class discovered: none beyond classes already covered — the
  evidence-first conclusion of the frontier mining.

## Overnight experiment table

| Exp | Baseline | Mechanism | Split | Pass | FAIL→PASS | PASS→FAIL | Net | Verdict |
|---|---|---|---|---|---|---|---|---|
| P-msheet-train | E009 tail | sheet-qualified writes | 3 train | 2 deterministic conversions | 2 | 0 | +2 | GREEN |
| E014 | E013 | H4 risk-gated best-of-N | dev60 | 80.0% | 1 | 4 | −3 | RED |
| H4B (sim) | H4 | executable-evidence selection | 129 train | 82.2% (=H4) | 0 | 0 | 0 | YELLOW |
| P-patch | best rollout | targeted patch | 6 train | — | 0 | 1 | −1 | RED |
| C24 2e-5 | control | corrected RSFT LR | canary24 | 12/12 sent, 2/12 opp | 0 | 0 | 0 | YELLOW |
| H12-R0 | base ctl 14/24 | REINFORCE, reward R0 continuous | canary24 | 13/24 (12/12 sent, 1/12 opp) | 0 | 1 opp | −1 (noise) | YELLOW safe/neutral |
| H12-R1 | base ctl 14/24 | REINFORCE, reward R1 discrete | canary24 | 13/24 (12/12 sent, 1/12 opp) | 0 | 1 opp | −1 (noise) | YELLOW safe/neutral |
| H12-R2 | base ctl 14/24 | REINFORCE, reward R2 hybrid | canary24 | 14/24 (12/12 sent, 2/12 opp) | 0 | 0 | 0 | YELLOW safe/neutral |
| H11 probe | E009 truncation class | 40k conditional rung | 8 train | killed (memory incident) | — | — | — | UNRUN |
| H10 probe | E009 exec class | sandboxed openpyxl agent | 10 train | killed (memory incident) | — | — | — | UNRUN |
| P8 local_test | dev 85.0% | frozen finalist, single confirmation | 60 | **91.7%** (55/60), cell 96.9% | — | — | — | GREEN |
| P9 full-400 (E015) | E009 76.25% | frozen finalist measurement | 400 | **78.0%** (312/400), sheet-lvl 65.6%, 0 missing, trace-audit CLEAN | — | — | +7 net vs E009 | GREEN — submission run |

## Active champion architecture (real, in execution order)

1. Champion attempt: values-only prompt, baseline serialisation, 24k budget
   (byte-stable vs E004 lineage). Skipped only when provably unwinnable
   (answer outside 120×30 view / >300 cells).
2. Golden-free health check (truncation, parse damage, static formula issues,
   recalc error values on our own output).
3. Gated escalation: coverage serialisation (formula-visible) + formula-
   permitting prompt at 32k; one evidence-fed repair.
4. Structural invariants (completeness incl. all-empty, column-type
   consistency) → one guarded structural repair (changes allowlisted).
5. Selection: healthiest artifact, ties to champion. Multi-sheet addresses
   sheet-qualified throughout.
6. Writer: coercion (ISO dates/times), formula prefixing, unmerge; salvage
   parser behind strict parse.

## Cost / runtime (approx)
[PENDING final tally] Paid sampled runs tonight: E014 (+partial killed run),
3 canaries ×2 attempts (memory incident), probes; replays/offline analyses:
free. Two macOS low-memory incidents (external 16GB of Docker VM/apps on
24GB RAM); Docker Desktop quit — relaunch before packaging retest.

## Rejected mechanisms
H4 (as frozen: blind-prompt candidate pools outvote sighted artifacts on
view-doomed tasks — H4C route-matched fix registered, unrun), H4B (redundant
on values pools), patch repair (consensus-wrong defeats golden-free
triggers), discrete reward R1 [pending canary but offline-predicted
under-informative], LR escalation beyond 2e-5 (frozen stop), RLVR
(unmet launch condition), per-cell consensus (frankensheet, measured).

## Submission readiness
[PENDING: Docker relaunch + final cold retest, artifact refresh, SUBMISSION.md
final paragraph]

## Exact reproduction (frozen finalist)
```sh
cd research && uv run experiments/runner.py --id <ID> --split dev \
  --model Qwen/Qwen3.8-27B --harness h8-structural --prompt-version cascade-v1 \
  --temperature 0 --max-tokens 24576 --concurrency 6 --retry-policy "escalate+structural" -- \
  uv run inference/cascade_predict.py --out-dir "{out_dir}" --base-model Qwen/Qwen3.8-27B \
  --ids "{ids}" --concurrency 6 --max-tokens 24576
```
(Full-400: `--split all`, no cache flag. Docker: `docker run --rm --env-file
research/.env -v <data>:/data:ro -v <out>:/out superspreadsheets`.)
