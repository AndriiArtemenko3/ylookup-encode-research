# H13C — Full-train online RLVR (FROZEN before launch, 2026-09-06 ~07:55)

Additive arm; H13A (boundary online RLVR) and H13B (hard-mined RSFT) are
untouched. Question: does online verifier-based post-training benefit from
exposure to the ENTIRE legitimate TRAIN distribution rather than a mined
subset? Primary causal comparison: H13C vs H13A (task-population is the
changed variable). Secondary: H13C vs H13B (outcome optimization vs
imitation).

## Frozen configuration

| Knob | H13A (reference) | H13C | Matched? |
|---|---|---|---|
| Base checkpoint | base Qwen/Qwen3.8-27B + fresh LoRA | same (NOT from H13A weights) | ✔ |
| Pipeline | cookbook rl.train, importance_sampling, fresh rollouts | same code path | ✔ |
| LoRA rank | 32 | 32 | ✔ |
| LR | 1e-5 | 1e-5 | ✔ |
| Reward | R0 (1.0 / 0.2·acc / −0.1) via SpreadsheetEnv | same Env class | ✔ |
| Observations | route-matched (doomed→coverage+formulas, else champion) | same function | ✔ |
| max_tokens | 16384 | 16384 | ✔ |
| Rollout temperature | cookbook default | same | ✔ |
| Task universe | 56 frozen boundary groups (mixed / spread≥0.10) | **all 280 train tasks** | ✘ (the variable) |
| Group size K | 8 | **4** | ✘ deviation, documented |
| Groups/batch | 4 | **20** | ✘ deviation, documented |
| n_batches | 20 (80 group-presentations, tasks recur) | **14** (280 presentations, one full pass) | ✘ (consequence) |
| save_every | 8 | 4 (≈29/57/86% + final 100%) | ~ |

Deviations rationale (wall-clock, frozen now, not tuned later): a full-280
coverage pass at K=8 is ≈2,240 fresh ≤16k-token rollouts — not completable
before the 10:30 hard stop at any service concurrency we have evidence for.
K=4 gives 1,120 fresh rollouts (the amendment's own worked example) and
groups_per_batch=20 packs the pass into 14 optimizer updates. Effective
per-update batch is larger than H13A's; recorded as a known confound.

## Sampling policy (frozen)

Uniform, unweighted, seed-42 shuffle of the 280 train ids, partitioned
sequentially into 14 batches of 20 — every train task receives exactly one
rollout group (K=4). No curriculum, no weighting, no dev/local_test contact
anywhere (task list asserted ⊆ train split at build time). Goldens
verifier-side only (same Env; model never sees golden content). No multi-sheet
exclusions: fresh rollouts use the fixed sheet-qualified writer, and the
H13A exclusions were artifacts of stale stored rollouts, not of the tasks.

## Budget (frozen, option A: one genuine coverage pass)

- 280 task presentations = 280 unique tasks = 280 groups × K4 = 1,120 episodes
- 14 optimizer updates; assistant tokens recorded from metrics.jsonl
- Projected wall: ~7–9 min/batch ⇒ ~100–130 min from launch

## Evaluation protocol

Same frozen canary24 (12 sentinels + 12 opportunity; base control 14/24;
destructive = any sentinel regression). If final (or latest completed)
checkpoint is non-destructive on canary: ONE dev60. No retraining after dev.
If training cannot finish before the 10:30 stop: save latest checkpoint,
record unique-tasks-seen honestly, mark **INCOMPLETE — partial coverage**,
never present it as full-train.

## State machine

H13C-FREEZE → H13C-TRAIN → H13C-CANARY → (non-destructive) → H13C-DEV →
H13C-COMPARE, fully autonomous. Compare table at the end: base finalist vs
corrected RSFT vs H13A vs H13B vs H13C, with the five interpretation
outcomes from the amendment quoted verbatim in MORNING_REPORT.
