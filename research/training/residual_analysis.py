"""H3 target analysis: residual-error structure of near-hard tasks (TRAIN only).

    uv run training/residual_analysis.py --rollouts ../experiments/F1-rollouts

For every 0/G task whose best candidate reached >=0.70 cell accuracy, rebuild
each candidate's workbook from its stored response, compare against the golden
answer cells (training-side; official normalisation via sb.values_equal), and
report the residual structure:

- stability: |cells wrong in EVERY candidate| / |cells wrong in ANY candidate|
  (1.0 = perfectly systematic residual -> prime deterministic-repair target)
- shape: contiguous tail? single column? and flavor: empty / type-mismatch /
  identical-string (typed-vs-text) / near-numeric / other
- also prints the best-accuracy distribution of all viable (near+partial)
  hard tasks, for H2 reward-shaping design.

Analysis feeds generic repair-rule design; rules themselves must be invariants
developed on train and validated untuned on dev.
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from inference.parse import parse_answer_lenient
from inference.write import write_output
from sb import load_answer_values, load_dataset, recalculate, values_equal
from training.reward import train_ids


def flavor(exp, act):
    if act is None:
        return "empty"
    if str(exp) == str(act):
        return "typed-vs-text"
    try:
        if abs(float(exp) - float(act)) < 0.051:
            return "near-numeric"
        return "wrong-number"
    except (TypeError, ValueError):
        pass
    if type(exp) is not type(act):
        return "type-mismatch"
    return "wrong-value"


def candidate_wrong_cells(task, response, work):
    out = Path(work) / "cand.xlsx"
    try:
        answer, _ = parse_answer_lenient(response)
        write_output(task, answer, out)
        has_formula = any(isinstance(c.value, str) and c.value.startswith("=") for c in answer.cells)
        path = recalculate(out, work) if has_formula else out
        gold = load_answer_values(task["golden_xlsx"], task)
        pred = load_answer_values(path, task)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:80]
    wrong = {k: (g, pred.get(k)) for k, g in gold.items() if not values_equal(g, pred.get(k))}
    return wrong, None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rollouts", required=True)
    args = p.parse_args()
    root = Path(args.rollouts) / "rollouts"
    tasks = {t["id"]: t for t in load_dataset() if t["id"] in train_ids()}

    near, partial_accs = [], []
    for task_dir in sorted(root.iterdir()):
        records = [json.loads(f.read_text()) for f in sorted(task_dir.glob("*.json"))]
        if not records or any((r.get("score") or {}).get("pass") for r in records):
            continue
        accs = [((r.get("score") or {}).get("correct") or 0) / ((r.get("score") or {}).get("cells") or 1)
                for r in records]
        best = max(accs, default=0)
        if best >= 0.70:
            near.append((task_dir.name, best, records))
        elif best >= 0.20:
            partial_accs.append(round(best, 3))

    print(f"== best-accuracy distribution (H2 reward design) ==")
    print(f"near: {sorted(round(b,3) for _,b,_ in near)}")
    print(f"partial: {sorted(partial_accs)}\n")

    for tid, best, records in sorted(near, key=lambda x: -x[1]):
        task = tasks[tid]
        wrong_sets, notes = [], []
        for r in records:
            if not r.get("response"):
                continue
            with tempfile.TemporaryDirectory() as work:
                wrong, err = candidate_wrong_cells(task, r["response"], work)
            if wrong is not None:
                wrong_sets.append(wrong)
            else:
                notes.append(err)
        if not wrong_sets:
            print(f"{tid:<8} best={best:.3f}  (no rebuildable candidates: {notes[:1]})")
            continue
        every = set.intersection(*(set(w) for w in wrong_sets)) if wrong_sets else set()
        any_ = set.union(*(set(w) for w in wrong_sets))
        stability = len(every) / len(any_) if any_ else 0
        sample = list(every)[:4] or list(any_)[:4]
        flavors = Counter(flavor(*wrong_sets[0][c]) for c in (every or any_) if c in wrong_sets[0])
        cols = Counter("".join(ch for ch in c[1] if ch.isalpha()) for c in (every or any_))
        print(f"{tid:<8} best={best:.3f}  wrong/cand={[len(w) for w in wrong_sets]}  "
              f"stable={len(every)}/{len(any_)} ({stability:.0%})  cols={dict(cols.most_common(3))}  "
              f"flavors={dict(flavors)}")
        for c in sample[:3]:
            g, a = wrong_sets[0].get(c, ("?", "?"))
            print(f"    {c[0]}!{c[1]}: expected {g!r} got {a!r}")


if __name__ == "__main__":
    main()
