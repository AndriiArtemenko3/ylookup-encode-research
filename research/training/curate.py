"""Curate verified rollouts into an SFT dataset.

    uv run training/curate.py --rollouts ../experiments/F1-rollouts [--dry-run] \
        [--out ../experiments/F1-rollouts/sft_dataset.jsonl]

Keeps only candidates that (a) the official verifier scored as a full task
pass (reward == 1.0) and (b) parse strictly (clean JSON, no salvage) — the
training target must be exactly the behaviour we want served. Caps at 2
distinct responses per task so easy tasks cannot dominate, and drops exact
duplicates. Emits chat-format examples byte-identical to how the rollout was
produced (champion system prompt, prompt + FORMAT_HINT), so training stays
on-policy with the serving configuration.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from common import FORMAT_HINT, SYSTEM_PROMPT, parse_answer

MAX_PER_TASK = 2


def strict_parses(response: str) -> bool:
    try:
        parse_answer(response)
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rollouts", required=True)
    p.add_argument("--out")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    root = Path(args.rollouts)
    out_path = Path(args.out) if args.out else root / "sft_dataset.jsonl"

    kept, examples = Counter(), []
    stats = Counter()
    for task_dir in sorted((root / "rollouts").iterdir()):
        seen = set()
        for f in sorted(task_dir.glob("*.json")):
            r = json.loads(f.read_text())
            stats["candidates"] += 1
            if r.get("reward") != 1.0:
                stats["rejected_not_pass"] += 1
                continue
            if not r.get("response") or not strict_parses(r["response"]):
                stats["rejected_not_strict"] += 1
                continue
            if r["response"] in seen:
                stats["rejected_duplicate"] += 1
                continue
            if kept[r["task_id"]] >= MAX_PER_TASK:
                stats["rejected_task_cap"] += 1
                continue
            seen.add(r["response"])
            kept[r["task_id"]] += 1
            assert r["reward"] == 1.0
            examples.append({"task_id": r["task_id"], "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": r["prompt"] + FORMAT_HINT},
                {"role": "assistant", "content": r["response"]},
            ]})

    lengths = sorted(len(e["messages"][1]["content"]) + len(e["messages"][2]["content"]) for e in examples)
    print(f"examples: {len(examples)} from {len(kept)} tasks   {dict(stats)}")
    if lengths:
        mid = lengths[len(lengths) // 2]
        print(f"chars per example: p50={mid} max={lengths[-1]} (~tokens p50={mid // 4})")
    band = Counter()
    groups_file = root / "groups.jsonl"
    if groups_file.exists():
        for line in groups_file.read_text().splitlines():
            g = json.loads(line)
            band["easy 4/4" if g["passes"] == 4 else "learnable 1-3/4" if g["passes"] else "hard 0/4"] += 1
        print(f"task bands: {dict(band)}")
    if args.dry_run:
        print("dry-run: nothing written")
        return
    with out_path.open("w", encoding="utf-8") as f:
        for e in examples:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
