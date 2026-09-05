"""Harness v2 parser: strict first, then salvage complete cell entries.

The baseline parser (baseline/common.py::parse_answer) discards the entire
reply when the JSON is truncated mid-generation or has a minor syntax slip —
the task then falls back to the init workbook and every answered cell is
lost. Salvage recovers the complete {"cell": ..., "value": ...} objects that
were emitted before the cutoff.

No-regression by construction: salvage runs only where the strict parse
already failed, and its own failure reproduces exactly the old outcome
(init-workbook fallback). Pass_rate can only gain; cell_accuracy is measured,
not assumed, via replay diffs.

To avoid scooping draft entries out of visible reasoning, scanning starts at
the LAST occurrence of a "cells" array marker when one exists.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baseline"))

from common import SpreadsheetAnswer, parse_answer  # baseline strict parser

_CELL_ENTRY = re.compile(r'\{\s*"cell"')
_CELLS_MARKER = re.compile(r'"cells"\s*:')
_SCALAR = (str, int, float, bool, type(None))


def parse_answer_lenient(text: str) -> tuple[SpreadsheetAnswer, str]:
    """Returns (answer, mode) where mode is 'strict' or 'salvaged'. Raises if neither works."""
    try:
        return parse_answer(text), "strict"
    except Exception:
        pass

    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    markers = list(_CELLS_MARKER.finditer(cleaned))
    start = markers[-1].start() if markers else 0
    decoder = json.JSONDecoder()
    entries = []
    for m in _CELL_ENTRY.finditer(cleaned, start):
        try:
            obj, _ = decoder.raw_decode(cleaned, m.start())
        except json.JSONDecodeError:
            continue
        if (isinstance(obj, dict) and isinstance(obj.get("cell"), str)
                and "value" in obj and isinstance(obj["value"], _SCALAR)):
            entries.append({"cell": obj["cell"], "value": obj["value"]})
    if not entries:
        raise ValueError("no salvageable cell entries in reply")
    return SpreadsheetAnswer.model_validate({"cells": entries}), "salvaged"
