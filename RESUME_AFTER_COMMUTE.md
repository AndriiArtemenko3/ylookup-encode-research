# RESUME AFTER COMMUTE — continuity contract (written 09:02, adaptive 09:05)

Commute interruption is an infrastructure pause, NOT an experiment boundary.
No specs change on resume. H13B is COMPLETE — never rerun it.

**Adaptive mode (09:05)**: checkpoints are safety banks, not stop triggers.
Training continues until an explicit human departure signal ("LEAVING NOW" /
"LID IN 5" / "COMMUTE NOW") or the automatic cutoff (09:50 no new long
batches; 09:55 graceful stop; everything committed by 10:00). If an arm
finishes naturally before departure: save final checkpoint → frozen canary →
if safe AND constructive, the authorized dev evaluation. Docker retest is
already banked (PASS 09:03) — its completion does not stop training.

## Banked and immutable (do not touch)

- **E015 = the submission**: 78.0% (312/400), trace-audited, artifacts at
  repo root (predictions.jsonl, outputs/, traces/, run.log, results.json),
  committed. Late research must never endanger it.
- H13B hard-mined RSFT: complete; canary 13/24 (12/12 sentinels, 1/12 opp vs
  control 2/12) = safe/neutral. Checkpoint:
  `tinker://fa68e5b9-1800-560b-8447-cb2fce4aead2:train:0/sampler_weights/final`
- H13A step-8 canary: 14/24 = 12/12 sentinels, 2/12 opportunity
  (236-22, 250-20) — exactly base control; neutral, non-destructive.
- Docker: daemon restarted healthy 08:56; image superspreadsheets:latest
  (6928e689ee19) intact. Final goldenless cold retest launched 08:58 —
  result recorded in OVERNIGHT_STATE.json under morning.docker_retest.

## State at lid close (final values in OVERNIGHT_STATE.json["lid_close"])

- H13A online RLVR: target = newest checkpoint (step 16 expected ~09:15;
  save_every=8). Checkpoint paths in
  `experiments/H13A-online-rlvr/checkpoints.jsonl` — each line carries BOTH
  `state_path` (weights + optimizer, for exact training resume) and
  `sampler_path` (for canary sampling). Optimizer-state resume IS supported
  via state_path.
- H13C full-train RLVR v2 (269 sampleable / 11 whale-excluded, budget 280
  presentations / 14 updates): target = newest checkpoint (batch 8 expected
  ~09:12, batch 12 ~09:33 only if lid allows; save_every=4). Same
  checkpoints.jsonl semantics.

## Exact resume commands (after arrival)

```sh
cd /Users/andriimain/Desktop/Andrii_Ylookup_Hackathon/encode-hackathon/research
# 1) reconcile
git status && git log --oneline -3
tail -2 ../experiments/H13A-online-rlvr/checkpoints.jsonl
tail -2 ../experiments/H13C-fulltrain-rlvr/checkpoints.jsonl
# 2) resume training (cookbook rl.train auto-resumes from log_path's
#    checkpoints.jsonl using state_path; verified semantics: a fresh dir
#    starts at batch 0, a dir with checkpoints continues after the last one)
uv run training/h13_run.py   > ../experiments/h13a_resume.log 2>&1 &   # H13A → step 20
uv run training/h13c_run.py  > ../experiments/h13c_resume.log 2>&1 &   # H13C → batch 14
# 3) verify resume did NOT restart from zero: first new metrics.jsonl line
#    must show step > last checkpoint batch. If it shows step 0, STOP and
#    treat weights-only continuation: do not retrain from scratch silently.
```

## Canary recipe (per checkpoint)

```sh
uv run baseline/tinker_predict.py --out-dir ../experiments/<name> \
  --base-model Qwen/Qwen3.8-27B --model-path <sampler_path> \
  --ids "1925,30930,31915,35739,37229,37554,38703,105-24,177-6,192-22,343-20,388-47,254-34,290-27,32438,486-17,49667,50193,51090,51680,524-31,54590,236-22,250-20" \
  --max-tokens 24576 --concurrency 6
uv run experiments/replay.py --source <name> --id <name>-h2   # needs manifest.json (copy pattern from H13B-canary)
```
Verdict rule: sentinels must stay 12/12; constructive = opportunity above
control 2/12 in exact passes.

## Policy after 10:30 (submission-integration freeze)

Training/canaries/dev evaluations MAY continue after 10:30 as a non-blocking
research track. Submission integration is frozen: a post-trained model enters
the submission ONLY with safe canary + real frozen dev improvement (≥+2 net)
+ ample packaging time + zero risk to E015. Otherwise: preserved as
post-training research / live-judging evidence.

## Promotion gate (§7A, verbatim intent)

Promotion = same hypothesis/data-rule/reward/LR/LoRA, full preregistered
exposure — only from an already-authorized family, only on exact-task
constructive signals (≥+2 net opportunity vs matched control, or repeated
near-pass→exact conversions). Training reward alone, cell accuracy alone, or
a single lucky flip do NOT qualify. No post-hoc redesign, no canary rerolls.
Current status: H13B neutral (no promotion), H13A s8 neutral (continue plan),
H13C awaiting first canary.

## Dev60 (if an arm turns constructive)

ONE dev60 on the frozen dev split via the finalist harness comparison
protocol; ≥+2 net vs E013 (51/60) with no broad regression mechanism →
full-400 confirmation only if operationally feasible. No tuning on dev.
