"""Free offline analyses over existing rollout records (no sampling, no goldens
beyond the rewards already computed by the verifier).

    uv run training/analyze_rollouts.py --rollouts ../experiments/F1-rollouts

H2 pre-analysis — RLVR substrate: stratify 0/4-hard tasks by best continuous
verifier score (near >=0.70, partial 0.20-0.70, dead <0.20/malformed) and by
within-group reward variance. Gradient-dead groups (max-min < 0.02) cannot
drive group-relative advantages.

H4 stage-1 — validity-guided best-of-N simulation: select ONE complete
candidate per task by golden-free signals only (strict parse, un-truncated
shape, trajectory-level agreement with sibling candidates on parsed cells,
response wellformedness). Report pass@1 (uniform-candidate baseline),
selector pass, consensus-only pass, oracle any-pass@G. Rewards are used ONLY
to score the simulation afterwards, never inside the selector.
"""

import argparse
import json
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from common import parse_answer


def candidate_features(record):
    """Golden-free validity signals for one candidate."""
    response = record.get("response") or ""
    cells = None
    strict = False
    try:
        answer = parse_answer(response)
        cells = {c.cell.upper(): c.value for c in answer.cells}
        strict = True
    except Exception:
        pass
    return {
        "strict": strict,
        "cells": cells,
        "n_cells": len(cells) if cells else 0,
        "closed": response.rstrip().endswith("}"),
        "has_error_text": record.get("error") is not None,
    }


def agreement(cells_a, cells_b):
    if not cells_a or not cells_b:
        return 0.0
    keys = set(cells_a) | set(cells_b)
    return sum(cells_a.get(k) == cells_b.get(k) for k in keys) / len(keys) if keys else 0.0


def select(features):
    """Score candidates by validity + trajectory-level agreement; return index."""
    n = len(features)
    scores = []
    for i, f in enumerate(features):
        agr = sum(agreement(f["cells"], features[j]["cells"]) for j in range(n) if j != i) / max(n - 1, 1)
        scores.append((f["strict"], not f["has_error_text"], f["closed"], round(agr, 4), f["n_cells"], -i))
    return max(range(n), key=lambda i: scores[i])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rollouts", required=True)
    args = p.parse_args()
    root = Path(args.rollouts)

    groups = {}
    for task_dir in sorted((root / "rollouts").iterdir()):
        records = [json.loads(f.read_text()) for f in sorted(task_dir.glob("*.json"))]
        if records:
            groups[task_dir.name] = records

    # ---- H2: hard-band stratification
    near, partial, dead = [], [], []
    variance_bearing = 0
    for tid, records in groups.items():
        rewards = [r["reward"] for r in records]
        passes = sum(1 for r in records if (r.get("score") or {}).get("pass"))
        if passes:
            continue
        accs = [((r.get("score") or {}).get("correct") or 0) / ((r.get("score") or {}).get("cells") or 1)
                for r in records]
        best = max(accs) if accs else 0.0
        (near if best >= 0.70 else partial if best >= 0.20 else dead).append((tid, round(best, 3)))
        if max(rewards) - min(rewards) >= 0.02:
            variance_bearing += 1
    print("== H2: RLVR substrate among hard (0/G) tasks ==")
    print(f"near (best acc >=0.70):   {len(near):>3}  {sorted(near, key=lambda x: -x[1])[:8]}")
    print(f"partial (0.20-0.70):      {len(partial):>3}")
    print(f"dead/structural (<0.20):  {len(dead):>3}")
    print(f"reward-variance-bearing:  {variance_bearing:>3} of {len(near) + len(partial) + len(dead)}")

    # ---- H4: selector simulation
    n_tasks = len(groups)
    pass1 = sum(sum(1 for r in recs if (r.get('score') or {}).get('pass')) / len(recs)
                for recs in groups.values()) / n_tasks
    oracle = sum(any((r.get('score') or {}).get('pass') for r in recs) for recs in groups.values()) / n_tasks
    sel_pass = cons_pass = 0
    for tid, records in groups.items():
        feats = [candidate_features(r) for r in records]
        chosen = select(feats)
        if (records[chosen].get("score") or {}).get("pass"):
            sel_pass += 1
        agr_only = max(range(len(feats)), key=lambda i: sum(
            agreement(feats[i]["cells"], feats[j]["cells"]) for j in range(len(feats)) if j != i))
        if (records[agr_only].get("score") or {}).get("pass"):
            cons_pass += 1
    print("\n== H4: validity-guided best-of-N simulation (train rollouts) ==")
    print(f"pass@1 (uniform candidate):     {pass1:.3f}")
    print(f"consensus-agreement selector:   {cons_pass / n_tasks:.3f}")
    print(f"validity+agreement selector:    {sel_pass / n_tasks:.3f}")
    print(f"oracle any-pass@G ceiling:      {oracle:.3f}")
    print(f"selector recovers {(sel_pass / n_tasks - pass1) / max(oracle - pass1, 1e-9):.0%} of the oracle gap")


if __name__ == "__main__":
    main()
