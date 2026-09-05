# Human actions required

Only tasks that genuinely require the human. Engineering tasks do not belong here.

## 1. Confirm the mandatory base model identifier (BLOCKING for any paid run)

The hackathon slides (p.16) and `research/README.md` line 88 both say:

> **Qwen3.8-27B** — 59.0% one-shot pass rate on the 400

but the starter Tinker baseline (`research/baseline/tinker_predict.py`) uses
`Qwen/Qwen3-8B` in its examples, and "Qwen3.8-27B" does not correspond to an
obvious Hugging Face / Tinker model id.

**Please confirm with the organisers the exact mandatory base model / model
identifier for the research-track final system.** Do not let anyone resolve
this by guesswork; every training run and the final submission depend on it.

## 2. Provide TINKER_API_KEY

Add the API key generated from the Ylookup Hackathon Tinker organisation to
`research/.env` as `TINKER_API_KEY=...` (the file is gitignored; never commit
it). Until it exists, no Tinker inference or training is possible.

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
