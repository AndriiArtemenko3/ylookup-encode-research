# H13 — True Online RLVR + Hard-Mined Expert Iteration (FROZEN pre-training)

Hard wall-clock: research stops 10:30 (T-90). E015 untouched fallback.

## H13A — online RLVR (primary)
- Cookbook-native: `tinker_cookbook.rl.train.main(Config)` with a custom
  single-turn `Env` (fresh rollouts from the CURRENT policy each update,
  sampled logprobs handled by the recipe; loss importance_sampling default).
- Model Qwen/Qwen3.8-27B, LoRA r32, lr 1e-5, group_size 8, 4 groups/batch,
  target 20 steps (hard max 24), temp 0.7 via recipe default sampling,
  max_tokens 16384.
- Reward inside Env.step = R0 exactly (1.0 pass / 0.2·acc valid / −0.1
  invalid), official `evaluate.score_task` on TRAIN goldens post-hoc; the
  model never sees goldens.
- Route-matched observations (H4's lesson): the env builds the SAME view the
  finalist would — champion prompt normally; coverage+formula prompt when the
  deterministic doomed-check fires; multisheet clause when the answer spans
  sheets. Group members share the route by construction.
- Task list (FROZEN, TRAIN only): F1v2 groups with mixed pass (1..G-1) OR
  zero-pass with acc-spread ≥ 0.10; EXCLUDING all-candidates-capped groups
  (output-bound) and the multi-sheet-bug tasks (harness-era artifacts).
  List written to the run manifest at launch.
- Canary at step ~8 checkpoint (frozen canary24); destructive-only stop rule.
  Checkpoints ~8/16/final.

## H13B — hard-mined expert-iteration RSFT (secondary; RAM-gated)
- Dataset: reasoning-preserved verified-pass raw-token trajectories from
  boundary groups only (1..3/4 passes) + 20% uniformly sampled easy passes as
  retention regularizer; strict parse; dedupe; cap 2/task. Frozen before
  training. lr 2e-5, r32, bs8, 2 passes, sampled-token targets (sft2.py).
- Launch only after E015 sampling completes (local RAM policy).

## Evaluation & promotion (both branches)
Frozen canary24 first; any non-destructive checkpoint gets EXACTLY ONE dev60
via the finalist-compatible harness path. Promotion to challenge E015
requires ≥ +2 dev exact tasks AND no new regression channel AND sentinel
retention; +1 = research result only. One shadow full-400 only if promoted
AND clock permits. No retraining after dev; no local_test.
