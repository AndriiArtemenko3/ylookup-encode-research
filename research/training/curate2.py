"""F1v2 curation: reasoning-preserving RSFT dataset from raw-token rollouts.

    uv run training/curate2.py --rollouts ../experiments/F1v2-rollouts-reasoning-preserved \
        [--out ...] [--dry-run]

Small-data discipline (per approved directive):
- official task pass (reward == 1.0) AND strict final parse required;
- the training target is the EXACT sampled completion token ids (reasoning
  included) — never re-rendered text;
- exact-duplicate completions dropped (token-id identity);
- easy tasks (group all-pass) contribute at most 1 trajectory;
- learnable/boundary tasks at most 2 diverse trajectories;
- NO boundary oversampling in the first corrected experiment;
- zero-success tasks contribute nothing.

Reports exposure in ASSISTANT TOKENS, not epochs.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from common import parse_answer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rollouts", required=True)
    p.add_argument("--out")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    root = Path(args.rollouts)
    out_path = Path(args.out) if args.out else root / "sft_dataset_v2.jsonl"

    examples, stats = [], Counter()
    comp_lengths, prompt_tokens_total = [], 0
    band_of = {}
    for task_dir in sorted((root / "rollouts").iterdir()):
        pt = task_dir / "prompt_tokens.json"
        if not pt.exists():
            continue
        prompt_ids = json.loads(pt.read_text())["prompt_token_ids"]
        records = [json.loads(f.read_text()) for f in sorted(task_dir.glob("[0-9]*.json"))]
        passes = sum(1 for r in records if r.get("reward") == 1.0)
        band = "easy" if passes == len(records) else "learnable" if passes else "hard"
        band_of[task_dir.name] = band
        cap = {"easy": 1, "learnable": 2, "hard": 0}[band]
        seen, kept = set(), 0
        for r in records:
            stats["candidates"] += 1
            if kept >= cap:
                stats["rejected_task_cap"] += bool(r.get("reward") == 1.0)
                continue
            if r.get("reward") != 1.0:
                stats["rejected_not_pass"] += 1
                continue
            if not r.get("completion_token_ids"):
                stats["rejected_no_raw_tokens"] += 1
                continue
            try:
                parse_answer(r["response"])
            except Exception:
                stats["rejected_not_strict"] += 1
                continue
            key = tuple(r["completion_token_ids"][:64]) + (len(r["completion_token_ids"]),)
            if key in seen:
                stats["rejected_duplicate"] += 1
                continue
            seen.add(key)
            kept += 1
            comp_lengths.append(len(r["completion_token_ids"]))
            prompt_tokens_total += len(prompt_ids)
            examples.append({"task_id": r["task_id"], "band": band,
                             "prompt_token_ids": prompt_ids,
                             "completion_token_ids": r["completion_token_ids"]})

    comp_lengths.sort()
    n = len(comp_lengths)
    q = lambda f: comp_lengths[int(n * f)] if n else 0
    bands = Counter(band_of.values())
    print(f"examples: {len(examples)} from {len({e['task_id'] for e in examples})} tasks  {dict(stats)}")
    print(f"task bands: {dict(bands)}  | train-task coverage: {len({e['task_id'] for e in examples})}/{len(band_of)}")
    print(f"completion tokens: p10={q(.10)} p50={q(.50)} p90={q(.90)} max={comp_lengths[-1] if n else 0}")
    print(f"TOTAL assistant training tokens: {sum(comp_lengths):,} | prompt tokens: {prompt_tokens_total:,}")
    if args.dry_run:
        print("dry-run: nothing written")
        return
    with out_path.open("w") as f:
        for e in examples:
            f.write(json.dumps(e) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
