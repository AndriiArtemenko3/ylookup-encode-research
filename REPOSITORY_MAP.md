# Repository map

This repository preserves an **append-only experimental history**. That is
useful for reproducibility but makes the raw GitHub tree noisier than a
normal product repository. This page separates the canonical
submission/research path from supporting and historical artifacts.

## Start here

1. [README.md](README.md) — project overview, result, architecture, main research findings.
2. [SUBMISSION.md](SUBMISSION.md) — concise organizer-facing method write-up.
3. [results.json](results.json) — frozen E015 400-task score (78.0%, 400/400 graded).
4. [docs/EXPERIMENT_MAP.md](docs/EXPERIMENT_MAP.md) — chronological experiment lineage.
5. [DATASETS.md](DATASETS.md) — training-data and data-lineage map.
6. [docs/RESEARCH_APPENDIX.md](docs/RESEARCH_APPENDIX.md) — full research narrative.

## Top-level tree

```text
superspreadsheets-ylookup-encode/
├── README.md            project overview and results
├── SUBMISSION.md        organizer-facing method write-up
├── REPOSITORY_MAP.md    this page
├── DATASETS.md          data lineage index
├── EXPERIMENTS.md       append-only ablation log (negatives included)
├── Dockerfile           the judge container (frozen E015 finalist config)
├── results.json         scored public-400 evidence
├── predictions.jsonl    E015 predictions (runtime output 1 of 4)
├── run.log              E015 execution log (runtime output 2 of 4)
├── outputs/             E015 generated workbooks (runtime output 3 of 4)
├── traces/              E015 per-task inference traces (runtime output 4 of 4)
│
├── research/
│   ├── inference/       THE FINAL SYSTEM — the h8 cascade the judges run
│   ├── training/        post-training machinery (RSFT, REINFORCE, RLVR envs)
│   ├── experiments/     experiment/evaluation TOOLING (runner, diffing, replay, audits)
│   ├── splits/          frozen train/dev/local_test/canary24 definitions
│   ├── tests/           golden-isolation and integrity guards
│   ├── data/            benchmark download target (source data not vendored)
│   ├── baseline/        untouched starter implementation (measured reference)
│   ├── tools/           workbook inspection + sandboxed execution utilities
│   └── evaluate.py, sb.py   the official scorer (immutable upstream)
│
├── experiments/         experiment RUN ARTIFACTS (82 append-only run dirs)
│
└── docs/                research documentation (index: docs/README.md)
```

The distinction that is easiest to miss: **`research/experiments/` is
tooling** (code that runs and scores experiments) while **`experiments/` is
run artifacts** (the manifests, results and logs those tools produced). And
the five root artifacts `predictions.jsonl` + `outputs/` + `traces/` +
`run.log` + `results.json` are the **frozen E015 submission evidence** — the
first four are the container's runtime output contract, the fifth is our
scored-public-run evidence (runtime inference never produces it, since
scoring needs goldens).

## Canonical vs historical

| Category | Canonical paths | Meaning |
|---|---|---|
| Submission-critical | `Dockerfile`, `SUBMISSION.md`, `predictions.jsonl`, `outputs/`, `traces/`, `run.log` | what the judges execute and the run we hand in |
| Final scored evidence | `results.json`, `experiments/E015-finalist-400/` | the frozen 78.0% measurement |
| Final inference system | `research/inference/` | the code that produced it |
| Evaluation/research tooling | `research/experiments/`, `research/tests/` | runners, official-scorer diffing, replay, audits, guards |
| Post-training code | `research/training/` | rollouts, RSFT, REINFORCE, online-RLVR environments |
| Training/data lineage | `DATASETS.md`, `experiments/F1v2-rollouts-reasoning-preserved/`, `experiments/F1-rollouts/` | corpora + rollout metadata |
| Experiment history | `experiments/` (index: [experiments/README.md](experiments/README.md)) | every run ever made, append-only |
| Research documentation | `docs/` (index: [docs/README.md](docs/README.md)) | narratives, preregistrations, audits |
| Internal workflow records | `MORNING_REPORT.md`, `OVERNIGHT_CAMPAIGN.md`, `OVERNIGHT_STATE.json`, `RESUME_AFTER_COMMUTE.md`, `README_FACTS.md` | preserved operational history of how the weekend was run — **not required to understand or run the submission**; safe to ignore |

## How to read experiments/

You do not need to read every directory. The mental model:

- `E***` — measured system experiment / benchmark run
- `H***` — hypothesis branch (mechanism or training experiment)
- `F***` — training-data / fine-tuning pipeline stage
- `C24-*` / `*-canary*` — 24-task canary evaluations of trained checkpoints
- `P***` — supporting probe / confirmation
- Suffixes: `*-h2` = zero-token write-path replay; `*-smoke` = pipeline smoke
  test; `*-killed-partial` = preserved memory-incident remnants
- Numbering has honest gaps (E005/E010/E011 were never promoted from plans).

Canonical harness lineage:

```text
E001 baseline → E002 token budget → E003 typed writer → E004 parser/unmerge
→ E006/E007 negative probes → E008 evidence cascade → E009 first full-400
→ E013 finalist mechanisms → E014 negative selector → P8 one-touch local_test
→ E015 final 400 (submission)
```

Post-training branch:

```text
E012 first RSFT failure → F1v2 corrected trajectories → corrected RSFT
→ H12 reward ablation → H13B hard-mined RSFT → H13A online RLVR
→ H13C broad RLVR → H14 preregistered dose extension (future)
```

Full per-experiment detail: [docs/EXPERIMENT_MAP.md](docs/EXPERIMENT_MAP.md).

## Reading paths by audience

**Judge — 5 minutes:** [README.md](README.md) → [SUBMISSION.md](SUBMISSION.md) → [results.json](results.json) → [Dockerfile](Dockerfile) → [docs/EXPERIMENT_MAP.md](docs/EXPERIMENT_MAP.md)

**ML / research engineer — 15–30 minutes:** [README.md](README.md) → [docs/RESEARCH_APPENDIX.md](docs/RESEARCH_APPENDIX.md) → [docs/EXPERIMENT_MAP.md](docs/EXPERIMENT_MAP.md) → [DATASETS.md](DATASETS.md) → [research/training/](research/training/) → selected `experiments/*/manifest.json`

**Reproducer:** [SUBMISSION.md](SUBMISSION.md) → [Dockerfile](Dockerfile) → [research/inference/](research/inference/) → [research/splits/](research/splits/) → [research/tests/](research/tests/) → [experiments/E015-finalist-400/](experiments/E015-finalist-400/)
