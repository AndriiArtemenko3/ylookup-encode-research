# Human actions required

Only tasks that genuinely require the human. Engineering tasks do not belong here.

## 1. ~~Confirm the mandatory base model identifier~~ — RESOLVED 2026-09-05

Human confirmed the mandated model is **Qwen3.8-27B**. Verified: the canonical
identifier is **`Qwen/Qwen3.8-27B`** (official Qwen org on Hugging Face), and
the installed tinker-cookbook recommends renderer `qwen3_8_xhigh_reasoning`
for it. The `Qwen/Qwen3-8B` strings in `research/baseline/tinker_predict.py`
are upstream doc examples only (no code default) and are superseded by this
confirmation. All experiments use `Qwen/Qwen3.8-27B`.

## 2. TINKER_API_KEY provided — but its project is READ-ONLY (BLOCKING)

Key added to `research/.env` 2026-09-05 and it authenticates: `whoami` resolves
to your account in the org, and `get_server_capabilities` lists
`Qwen/Qwen3.8-27B` as sampleable + trainable (65k context). However every
attempt to create a sampling session fails with:

> 400 — "This project is read-only and cannot be modified."

The SDK has no project-listing call; a writable project id could only be
passed explicitly as `ServiceClient(project_id=...)`.

**Please do one of:**
1. Check the Tinker console (https://tinker.thinkingmachines.ai) for a
   writable project for your team and give me its project id, or
2. Ask the organisers / research desk why the hackathon key's default project
   is read-only (likely the team invite or project provisioning is incomplete)
   and get either a corrected key or a writable project.

Optional: `OPENROUTER_API_KEY=...` in the same file if we also want the
OpenRouter one-shot baseline (`baseline/llm_predict.py`) for reference numbers.

## 3. Ask organisers for the "reference Dockerfile"

The submission slide says "Start from the reference Dockerfile, swap in your
pipeline", but the starter repository contains no Dockerfile. Ask where it
lives (Discord pin, separate repo, ...), or confirm we should write our own
from scratch against the `/data` (read-only) → `/out` contract.

## 4. Approve credit spend before material runs

Per our operating principles, no full 400-task paid run, fine-tuning or RL
starts without explicit approval. The first spend request will be:
one-task Tinker smoke test (negligible), then an untouched-baseline dev-split
run, then the full-400 baseline. Each will be requested explicitly.

## 5. Thinking Machines / Tinker invite (if not already done)

Give your Google Cloud account address at the research desk so the Tinker
organisation invite can be sent (slides: invites are sent manually at
team-forming).
