# experiments/ — run directory index

**You do not need to read every directory.** For the main research story,
follow only the *Canonical milestone runs* below — everything else is
supporting rollout, replay, canary, failed-branch, or historical evidence.
Wider context: [../REPOSITORY_MAP.md](../REPOSITORY_MAP.md) ·
[../docs/EXPERIMENT_MAP.md](../docs/EXPERIMENT_MAP.md) ·
[../DATASETS.md](../DATASETS.md).

Directory names look heterogeneous because they preserve **append-only
historical experiment IDs** — runs are never renamed or rewritten after they
execute, so manifests, diffs and logs stay verifiable.

Each run directory contains a `manifest.json` (git commit, exact command,
parameters), the official scorer's `results.json` where the run was scored,
and event/trace logs. `*-h2` suffixes are zero-token write-path replays of a
stored run; `*-killed-partial` are preserved remnants of host memory-incident
kills (kept for the incident record, not results); `*-smoke` are pipeline
smoke tests.

## Canonical milestone runs

| Directory | What it is | Result |
|---|---|---|
| `E001-baseline-dev` | untouched starter, dev | 46.7% |
| `E008-cascade-dev` | dev champion (evidence cascade) | 83.3% |
| `E009-champion-400` | first frozen full-400 measurement | 76.25% |
| `E013-h3-dev` | finalist config, dev | 85.0% |
| `P8-localtest-finalist` | one-touch held-out confirmation | 91.67% |
| `E015-finalist-400` | **the submission run** (also copied to repo root) | **78.0%** |
| `F1v2-sft-lr1e5` / `-lr2e5` | corrected RSFT checkpoints | safe/neutral |
| `H12-R0/R1/R2` (+ `-canary[-h2]`) | reward-ablation arms + canaries | safe/neutral |
| `H13B-hardmined-rsft` (+ `H13B-canary[-h2]`) | hard-mined RSFT + canary | safe/neutral |
| `H13A-online-rlvr` | online RLVR training logs + checkpoints | eval pending |
| `H13C-fulltrain-rlvr` | full-train RLVR training logs + checkpoints | eval pending |

Everything else is a probe, canary, rollout store or replay supporting one of
the milestones above; its `manifest.json` names its parent experiment.
