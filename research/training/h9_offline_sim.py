"""H9 offline simulation: semantic-uncertainty consensus over existing rollouts.

    uv run training/h9_offline_sim.py [--rollouts ../experiments/F1-rollouts]
                                      [--sample 120] [--seed 7]

For every train task with >= 3 parseable candidates (parse_answer_lenient;
canonical agreement is writer-equivalent via coerce_value inside
inference.consensus.canonicalize) this script compares four policies:

  pass@1     mean per-candidate pass (uniform pick),
  selected   H4-style golden-free validity+agreement selection
             (training/analyze_rollouts.select),
  consensus  a NEW artifact built from cells where >= 2 of the first 3
             parseable candidates agree after canonicalization,
  oracle@N   any candidate passes.

Candidate-level metrics come from the rewards already stored in the rollout
records. The consensus artifact is new, so it is scored against the golden
workbook with evaluate.score_task — offline TRAIN analysis only, explicitly
sanctioned here and kept out of inference/ code. LibreOffice recalculation is
invoked only when the consensus artifact actually contains formulas.
"""

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
for p in (RESEARCH, RESEARCH / "baseline", RESEARCH / "training"):
    sys.path.insert(0, str(p))

from analyze_rollouts import candidate_features, select
from common import SpreadsheetAnswer

from evaluate import score_task
from inference.consensus import agreement_stats, build_consensus
from inference.parse import parse_answer_lenient
from inference.write import write_output
from sb import DEFAULT_DATASET, load_dataset


def parse_candidates(records):
    """(record, cells) for each record whose response parses leniently."""
    out = []
    for rec in records:
        try:
            answer, _mode = parse_answer_lenient(rec.get("response") or "")
        except Exception:
            continue
        cells = {(None, c.cell.upper()): c.value for c in answer.cells}
        out.append((rec, cells))
    return out


def passed(record) -> bool:
    return bool((record.get("score") or {}).get("pass"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollouts", default=str(RESEARCH.parent / "experiments" / "F1-rollouts"))
    ap.add_argument("--sample", type=int, default=120, help="max tasks to simulate (0 = all)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    tasks_by_id = {t["id"]: t for t in load_dataset(DEFAULT_DATASET)}
    root = Path(args.rollouts) / "rollouts"
    task_ids = sorted(d.name for d in root.iterdir() if d.is_dir())
    if args.sample and args.sample < len(task_ids):
        task_ids = sorted(random.Random(args.seed).sample(task_ids, args.sample))

    started = time.time()
    n_sim = 0
    pass1_sum = 0.0
    sel_pass = cons_pass = oracle_pass = 0
    cons_only = sel_only = both = neither = 0
    synthesis_wins = []      # consensus passes, no input candidate passed
    frankensheet_fails = []  # an input candidate passed, consensus artifact failed
    score_errors = []
    skipped = []
    flagged_fracs = []
    unanimous_fracs = []
    formula_tasks = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for tid in task_ids:
            task = tasks_by_id.get(tid)
            records = [json.loads(f.read_text())
                       for f in sorted(root.joinpath(tid).glob("*.json"), key=lambda f: int(f.stem))]
            if task is None or not records:
                skipped.append((tid, "no task/records"))
                continue
            parseable = parse_candidates(records)
            if len(parseable) < 3:
                skipped.append((tid, f"only {len(parseable)} parseable"))
                continue
            n_sim += 1

            # candidate-level metrics from stored rewards
            pass1_sum += sum(passed(r) for r in records) / len(records)
            oracle_pass += any(passed(r) for r in records)
            feats = [candidate_features(r) for r in records]
            sel_ok = passed(records[select(feats)])
            sel_pass += sel_ok

            # consensus artifact from the first 3 parseable candidates
            trio = parseable[:3]
            cand_cells = [cells for _, cells in trio]
            stats = agreement_stats(cand_cells)
            unanimous_fracs.append(stats["fraction_unanimous"])
            consensus, flagged = build_consensus(cand_cells)
            flagged_fracs.append(len(flagged) / max(len(consensus) + len(flagged), 1))

            answer = SpreadsheetAnswer.model_validate(
                {"cells": [{"cell": coord, "value": v} for (_, coord), v in consensus.items()]})
            out_path = tmp / f"{tid}.xlsx"
            has_formula = any(isinstance(v, str) and v.startswith("=") for v in consensus.values())
            formula_tasks += has_formula
            try:
                write_output(task, answer, out_path)
                result = score_task(task, out_path, has_formula, tmp / "recalc")
            except Exception as e:
                result = {"status": "error", "error": str(e)[:120]}
            if result.get("status") != "graded":
                score_errors.append((tid, result.get("status"), result.get("error", "")))
            cons_ok = bool(result.get("pass"))
            cons_pass += cons_ok

            trio_passed = any(passed(r) for r, _ in trio)
            if cons_ok and not trio_passed:
                synthesis_wins.append(tid)
            if trio_passed and not cons_ok:
                frankensheet_fails.append(tid)
            if cons_ok and sel_ok:
                both += 1
            elif cons_ok:
                cons_only += 1
            elif sel_ok:
                sel_only += 1
            else:
                neither += 1
            out_path.unlink(missing_ok=True)

    elapsed = time.time() - started
    n = max(n_sim, 1)
    print("== H9 offline simulation: consensus artifact vs selection (train rollouts) ==")
    print(f"tasks in scope: {len(task_ids)}   simulated (>=3 parseable): {n_sim}   skipped: {len(skipped)}")
    print(f"pass@1 (uniform candidate):     {pass1_sum / n:.3f}")
    print(f"selected (H4 validity+agree):   {sel_pass / n:.3f}")
    print(f"consensus artifact (>=2 of 3):  {cons_pass / n:.3f}")
    print(f"oracle any-pass@N:              {oracle_pass / n:.3f}")
    print()
    print(f"consensus vs selection: both {both}, consensus-only {cons_only}, "
          f"selection-only {sel_only}, neither {neither}")
    print(f"synthesis wins (consensus passes, no input candidate passed): {synthesis_wins}")
    print(f"frankensheet fails (an input candidate passed, consensus failed): {frankensheet_fails}")
    print(f"mean flagged-cell fraction: {sum(flagged_fracs) / n:.3f}   "
          f"mean unanimous-cell fraction: {sum(unanimous_fracs) / n:.3f}")
    print(f"consensus artifacts containing formulas (recalced): {formula_tasks}")
    if score_errors:
        print(f"scoring errors ({len(score_errors)}): {score_errors[:5]}")
    if skipped:
        print(f"skipped detail (first 5): {skipped[:5]}")
    print(f"runtime: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
