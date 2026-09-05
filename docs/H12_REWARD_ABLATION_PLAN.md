# H12 — Matched Reward-Function Ablation (FROZEN before training)

## Method selection (recorded per directive §15)
Installed `tinker` exposes loss_fns {cross_entropy, importance_sampling, ppo,
cispo, dro}; the cookbook RL recipe requires per-token SAMPLED logprobs,
which our stored rollouts did not capture. Rather than resample ~8M tokens,
all arms train as **on-policy policy-gradient (REINFORCE)**: stored F1v2
trajectories were sampled from exactly the base policy being updated; datum
weights carry signed group-relative advantages (verified live: negative
weights accepted). One data pass, conservative LR → bounded off-policy drift.
Label: LoRA + on-policy policy-gradient. NOT PPO, NOT reward-weighted SFT.

## Matched constants (all arms)
Base Qwen/Qwen3.8-27B; LoRA r32; lr 1e-5 linear decay; AdamParams(.9,.95,1e-8);
batch = 4 groups (16 sequences); 1 pass over the frozen band; shuffle seed 42;
max_length 32768; checkpoints at 25/50/100% of band-token exposure; canary24;
same champion prompt/harness at eval; dev-60 once per surviving arm.

## Frozen learnable band (identical for all arms; TRAIN only)
Groups from F1v2-rollouts with EITHER (a) ≥1 pass AND ≥1 non-pass candidate,
OR (b) zero passes but candidate cell-accuracy spread ≥ 0.10. Membership
computed once, stored in the run manifest.

## Frozen reward definitions
Buckets (TRAIN-derived: non-pass wrong-cells p50=29; only 10 candidates sit
at wrong≤5 ∧ acc≥0.9):
- EXACT: official pass. NEAR_EXACT: wrong ≤ 5 AND acc ≥ 0.90.
- PARTIAL: acc ≥ 0.30. FAIL: valid, acc < 0.30. INVALID: unscorable.

R0 (control): 1.0 / 0.2·acc (any valid non-pass) / −0.1.
R1 (discrete): 1.0 / 0.5 / 0.2 / 0.02 / −0.1 by bucket.
R2 (hybrid): 1.0 / 0.45+0.10·acc / 0.15+0.10·acc / 0.02·acc / −0.1.

Offline diagnostics (measured, drove the freeze): informative groups
R0 76 · R1 53 · R2 69 /280; all-fail-still-ranked R0 30 · R1 7 · R2 23.
Prediction registered: R1 likely under-informs; R2 ≈ R0 + NEAR_EXACT margin.

## Advantages
adv_i = (r_i − mean_group) / (std_group + 1e-4), clipped to ±2; token weight
= adv / n_completion_tokens (reduction="none"); prompt tokens weight 0.

## Gates
Canary GREEN: ≥11/12 sentinels AND opportunity > control(2)+1. YELLOW: safe
neutral. RED (early-stop only for): ≥3 sentinel losses, malformed-output
runaway, or NLL instability. Matched budget is never extended for a promising
arm nor cut for a neutral one. Dev once per non-RED arm; no retraining after
dev. Replication rule (pre-committed): if top two arms differ by ≤1 dev task,
one seed replicate of BOTH those arms (seed 43), budget identical.
