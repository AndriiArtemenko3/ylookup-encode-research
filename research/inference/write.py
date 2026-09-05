"""Harness v1 write path: write model answers to the workbook faithfully.

The model can only emit JSON strings/numbers; Excel cells are typed. The
official comparison (sb.transform_value / values_equal) requires equal types
after normalisation, so a date the model answered correctly as the string
"2014-02-05 00:00:00" fails against a real datetime cell. E002 lost 9 of 60
dev tasks to exactly this.

coerce_value converts ONLY strict, full-string ISO shapes — the forms our own
serialisation prints datetime/time cells in, i.e. what the model echoes back
when the answer is a date. Anything else (partial matches, display formats
like "2021 02 24", AM/PM strings) is left verbatim: when a golden wants date
LOOKING text, it wants the text. Regression scan on E002: zero passing answer
cells contained these shapes.

harness log: v1 = baseline + coerce_value in the write path. Nothing else.
"""

import datetime
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import openpyxl

from sb import answer_cells

HARNESS_VERSION = "h1-faithful-write"

_ISO_DATETIME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_ISO_TIME = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")


def coerce_value(value):
    """Strict full-match ISO datetime/date/time strings -> typed objects; all else verbatim."""
    if not isinstance(value, str):
        return value
    s = value.strip()
    if m := _ISO_DATETIME.match(s):
        try:
            return datetime.datetime(*map(int, m.groups()))
        except ValueError:  # e.g. month 13: not a date, keep the text
            return value
    if m := _ISO_DATE.match(s):
        try:
            return datetime.datetime(*map(int, m.groups()))
        except ValueError:
            return value
    if m := _ISO_TIME.match(s):
        h, mi, sec = map(int, m.groups())
        if h < 24 and mi < 60 and sec < 60:
            return datetime.time(h, mi, sec)
    return value


def write_output(task: dict, answer, out_path: Path) -> None:
    """Baseline write_output (baseline/common.py:79) plus coerce_value per cell."""
    cells = {c.cell.upper(): c.value for c in answer.cells}
    shutil.copy(task["init_xlsx"], out_path)
    wb = openpyxl.load_workbook(out_path)
    for sheet, coord in answer_cells(task, wb):
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
        if coord in cells:
            ws[coord] = coerce_value(cells[coord])
    wb.save(out_path)
