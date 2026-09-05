"""H9 semantic-uncertainty layer: golden-free N-candidate consensus.

Inference-side only. Works purely on candidate answers (parsed cell dicts):
canonicalize values the same way the official scorer normalises them, measure
cross-candidate agreement, build a majority-consensus artifact, and emit a
targeted repair prompt for the cells the candidates disagree on. No golden
data is ever read here — sb.transform_value is pure value arithmetic and
inference.write.coerce_value is the writer's own type coercion.

harness log: h9 = consensus layer over N sampled candidates. Nothing else.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sb import transform_value  # pure normalisation arithmetic, no file I/O

from inference.write import coerce_value

CellKey = tuple  # (sheet_or_None, coord)


def canonicalize(value):
    """Writer-equivalent canonical form of one candidate cell value.

    Mirrors the official normalisation style: the writer's ISO string ->
    typed coercion first (what would land in the workbook), then the scorer
    arithmetic — numbers round(float, 2), datetimes -> Excel serial rounded
    to 0 dp, times -> "HH:MM" text. Empty string and None collapse to None.
    """
    v = transform_value(coerce_value(value))
    if v in ("", None):
        return None
    return v


def _key(value):
    """Hashable equality key honouring the scorer's type-sensitive compare."""
    v = canonicalize(value)
    return (type(v).__name__, v)


def agreement_stats(candidate_cells: list[dict]) -> dict:
    """Agreement statistics over N candidates' cell dicts {(sheet, coord): value}.

    Returns per-cell agreement counts (max #candidates proposing the same
    canonical value), whole-answer agreement (fraction of candidate pairs
    with identical canonical answers), a pairwise disagreement matrix
    (fraction of union cells that differ), fraction of cells reaching
    majority (>= 2 of 3 style), and fraction unanimous.
    """
    n = len(candidate_cells)
    all_keys = sorted({k for cells in candidate_cells for k in cells})
    per_cell = {}
    majority_needed = 2 if n <= 3 else n // 2 + 1
    for key in all_keys:
        proposals = [_key(cells[key]) for cells in candidate_cells if key in cells]
        counts = {}
        for p in proposals:
            counts[p] = counts.get(p, 0) + 1
        top = max(counts.values()) if counts else 0
        per_cell[key] = {"proposals": len(proposals), "top_agreement": top,
                         "distinct": len(counts)}
    disagree = [[0.0] * n for _ in range(n)]
    whole_pairs = agree_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = candidate_cells[i], candidate_cells[j]
            union = set(a) | set(b)
            diff = sum(1 for k in union
                       if k not in a or k not in b or _key(a[k]) != _key(b[k]))
            frac = diff / len(union) if union else 0.0
            disagree[i][j] = disagree[j][i] = round(frac, 4)
            whole_pairs += 1
            agree_pairs += diff == 0
    n_cells = len(all_keys) or 1
    return {
        "n_candidates": n,
        "n_cells": len(all_keys),
        "per_cell": per_cell,
        "whole_answer_agreement": round(agree_pairs / whole_pairs, 4) if whole_pairs else 1.0,
        "pairwise_disagreement": disagree,
        "fraction_majority": round(
            sum(c["top_agreement"] >= majority_needed for c in per_cell.values()) / n_cells, 4),
        "fraction_unanimous": round(
            sum(c["top_agreement"] == n for c in per_cell.values()) / n_cells, 4),
    }


def build_consensus(candidates: list[dict]) -> tuple[dict, dict]:
    """Majority consensus over candidate cell dicts {(sheet, coord): value}.

    A cell gets a consensus value when >= 2 of 3 candidates (a strict
    majority for larger N) agree after canonicalization; the stored value is
    the first proposer's raw value so the writer keeps its type coercion.
    Cells with no majority are flagged with every candidate proposal.
    """
    n = len(candidates)
    majority_needed = 2 if n <= 3 else n // 2 + 1
    consensus, flagged = {}, {}
    for key in sorted({k for cells in candidates for k in cells}):
        groups = {}  # canonical key -> [raw values in candidate order]
        for cells in candidates:
            if key in cells:
                groups.setdefault(_key(cells[key]), []).append(cells[key])
        best = max(groups.values(), key=len)
        if len(best) >= majority_needed:
            consensus[key] = best[0]
        else:
            flagged[key] = [cells.get(key) for cells in candidates]
    return consensus, flagged


def make_repair_prompt(instruction_snippet: str, disagreements: dict) -> str:
    """Short targeted repair prompt from instruction + disagreement locations.

    Uses only the instruction text and the candidates' own proposals for the
    contested cells — no reference answers of any kind.
    """
    lines = []
    for (sheet, coord), proposals in sorted(disagreements.items()):
        where = f"{sheet}!{coord}" if sheet else coord
        shown = ", ".join(repr(p) for p in proposals[:4])
        lines.append(f"- {where}: candidates proposed {shown}")
    return (
        "Several attempts at this spreadsheet task disagree on a few cells.\n"
        f"Instruction: {instruction_snippet.strip()[:400]}\n"
        "Contested cells and the values proposed so far:\n"
        + "\n".join(lines[:40])
        + '\n\nRe-derive ONLY these cells from the instruction and workbook. '
        'Reply with JSON only: {"cells": [{"cell": "A1", "value": ...}]}'
    )
