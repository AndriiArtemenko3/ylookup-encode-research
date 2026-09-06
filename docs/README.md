# Documentation index

The authoritative map of every document in this repository, grouped by what a
reader needs. Experiment IDs (E/H/P/C24/F*) are decoded in
[EXPERIMENT_MAP.md](EXPERIMENT_MAP.md).

## Start here (judge-facing)

- [../README.md](../README.md) — the project: results, generalization story, architecture, reproduction.
- [../SUBMISSION.md](../SUBMISSION.md) — submission form content and artifact layout.
- [RESEARCH_APPENDIX.md](RESEARCH_APPENDIX.md) — the full research narrative.
- [../EXPERIMENTS.md](../EXPERIMENTS.md) — the append-only ablation log, negatives included.
- [RESIDUAL_FRONTIER.md](RESIDUAL_FRONTIER.md) — what still fails after the finalist, and why.
- [EXPERIMENT_MAP.md](EXPERIMENT_MAP.md) — plain-English decoder + chronological lineage of every experiment.

## Core system research

- [BASELINE_ANALYSIS.md](BASELINE_ANALYSIS.md) — source-cited analysis of the untouched starter baseline. *(status: adopted as the measured reference point)*
- [E009_RESIDUAL_AUDIT.md](E009_RESIDUAL_AUDIT.md) — individual classification of all 95 failures of the first full-400 run. *(status: adopted; drove the residual-tail mechanisms)*
- [FORMULA_TAXONOMY.md](FORMULA_TAXONOMY.md) — taxonomy of formula usage mined from trajectories. *(status: adopted as evidence for the gated formula policy)*
- [RESEARCH_PLAN.md](RESEARCH_PLAN.md) — the original phase plan for the weekend. *(status: historical; superseded by the hypothesis registry in EXPERIMENTS.md)*

## Post-training research

- [H12_REWARD_ABLATION_PLAN.md](H12_REWARD_ABLATION_PLAN.md) — frozen preregistration of the reward-function ablation (R0/R1/R2). *(status: executed; all arms safe/neutral)*
- [H13_ONLINE_RLVR_PLAN.md](H13_ONLINE_RLVR_PLAN.md) — frozen preregistration of true online RLVR (H13A) and hard-mined expert iteration (H13B). *(status: executed; H13B safe/neutral, H13A evaluation pending at submission)*
- [H13C_FULLTRAIN_PLAN.md](H13C_FULLTRAIN_PLAN.md) — frozen preregistration of full-train-coverage online RLVR, incl. the unsampleable-whale guard incident. *(status: trained; evaluation pending at submission)*
- [H14_DOSE_EXTENSION_PLAN.md](H14_DOSE_EXTENSION_PLAN.md) — preregistered post-submission dose-extension follow-up. *(status: preregistered, not launched)*
- Training code: [../research/training/](../research/training/) (rollout capture, curation, RSFT, REINFORCE, RLVR environments and launchers).

## Historical / preregistered experiment plans

- [H3_DEV_PLAN.md](H3_DEV_PLAN.md) — golden-free structural verification & repair. *(status: adopted — became the finalist's structural-invariant stage)*
- [H4_DEV_PLAN.md](H4_DEV_PLAN.md) — validity-guided best-of-N selection. *(status: rejected on dev — net −3; kept as a mechanism-attributed negative)*
- [H4B_VERIFIER_PLAN.md](H4B_VERIFIER_PLAN.md) — execution-backed selection variant. *(status: redundant — offline-identical to H4 on values pools; never promoted)*
- [H11_LADDER_PLAN.md](H11_LADDER_PLAN.md) — conditional 40k deeper-escalation rung. *(status: unrun — probe killed by a host memory incident; registered future work)*
- [HACKATHON.md](HACKATHON.md) — the organizer's original starter brief. *(status: historical; kept for provenance)*

## Internal / operational records (not research claims)

Workflow logs kept for transparency; they document how the weekend was run,
not what was measured:

- [HUMAN_ACTIONS.md](HUMAN_ACTIONS.md) — human-in-the-loop requests and resolutions.
- [../MORNING_REPORT.md](../MORNING_REPORT.md) — the overnight campaign's consolidated report.
- [../OVERNIGHT_CAMPAIGN.md](../OVERNIGHT_CAMPAIGN.md) / [../OVERNIGHT_STATE.json](../OVERNIGHT_STATE.json) — the autonomous overnight state machine and its incident log.
- [../RESUME_AFTER_COMMUTE.md](../RESUME_AFTER_COMMUTE.md) — continuity contract for a mid-campaign laptop commute.
- [../README_FACTS.md](../README_FACTS.md) — the source-of-truth fact pack behind the README, with a measured/inferred/in-flight claim audit.
