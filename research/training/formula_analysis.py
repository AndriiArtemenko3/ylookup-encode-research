"""Formula-primitive taxonomy mined from the TRAIN split only.

    uv run training/formula_analysis.py [--out ../docs/FORMULA_TAXONOMY.md]

Evidence sources, strongest first (per research plan): the 280 train-split
golden workbooks (what answers actually look like), then existing formulas in
train INPUT workbooks (what real spreadsheets already contain). dev and
local_test are never opened — they stay honest holdouts.

Reports: function frequencies, co-occurrence pairs (INDEX+MATCH, ...),
cross-sheet reference rate, formula presence by instruction type, and which
functions fall outside the classic LibreOffice-safe tier (the _xlfn prefix
tier the harness must handle). Feeds prompt archetypes and any Phase F
training curriculum. Training-side module: reading goldens here is sanctioned.
"""

import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))

import openpyxl

from sb import load_dataset

FUNC = re.compile(r"(?<![A-Z0-9_.])([A-Z][A-Z0-9]{1,15})\(")
SHEET_REF = re.compile(r"[A-Za-z_'][^!]{0,40}!")


def formulas_in(path: str) -> list[str]:
    out = []
    try:
        wb = openpyxl.load_workbook(path, data_only=False)
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        out.append(cell.value.upper())
        wb.close()
    except Exception:
        pass
    return out


def analyse(tasks):
    from inference.write import _XLFN_FUNCS, _XLWS_FUNCS
    modern = _XLFN_FUNCS | _XLWS_FUNCS
    stats = {}
    for source in ("golden", "init"):
        funcs, pairs, cross, n_wb_with, lengths = Counter(), Counter(), 0, 0, []
        by_type = Counter()
        for t in tasks:
            path = t["golden_xlsx"] if source == "golden" else t["init_xlsx"]
            if not path:
                continue
            fs = formulas_in(path)
            if fs:
                n_wb_with += 1
                by_type[t["instruction_type"][:5]] += 1
            for f in fs:
                found = sorted({m.group(1) for m in FUNC.finditer(f)})
                funcs.update(found)
                pairs.update(combinations(found, 2))
                cross += bool(SHEET_REF.search(f))
                lengths.append(len(f))
        stats[source] = {"workbooks_with_formulas": n_wb_with, "by_instruction_type": dict(by_type),
                         "total_formulas": len(lengths),
                         "top_functions": funcs.most_common(25),
                         "top_pairs": [("+".join(p), c) for p, c in pairs.most_common(12)],
                         "cross_sheet_refs": cross,
                         "modern_tier_hits": [(f, c) for f, c in funcs.items() if f in modern],
                         "mean_length": round(sum(lengths) / len(lengths), 1) if lengths else 0}
    return stats


def render(stats, n_tasks) -> str:
    lines = [f"# Formula taxonomy — train split ({n_tasks} tasks)\n",
             "Mined by `research/training/formula_analysis.py`. dev/local_test never opened.\n"]
    for source, s in stats.items():
        lines.append(f"\n## {'Golden answers' if source == 'golden' else 'Input workbooks'}\n")
        lines.append(f"- workbooks containing formulas: {s['workbooks_with_formulas']}"
                     f" (by type: {s['by_instruction_type']})")
        lines.append(f"- total formulas: {s['total_formulas']}, mean length {s['mean_length']} chars,"
                     f" cross-sheet refs: {s['cross_sheet_refs']}")
        lines.append(f"- modern (_xlfn tier) usage: {s['modern_tier_hits'] or 'none'}")
        lines.append("\n| Function | Count |\n|---|---|")
        lines += [f"| {f} | {c} |" for f, c in s["top_functions"]]
        lines.append("\n| Co-occurrence | Count |\n|---|---|")
        lines += [f"| {p} | {c} |" for p, c in s["top_pairs"]]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", help="write a markdown report here")
    args = p.parse_args()
    train = set(json.loads((RESEARCH / "splits" / "train.json").read_text()))
    tasks = [t for t in load_dataset() if t["id"] in train]
    stats = analyse(tasks)
    report = render(stats, len(tasks))
    print(report)
    if args.out:
        Path(args.out).write_text(report)


if __name__ == "__main__":
    main()
