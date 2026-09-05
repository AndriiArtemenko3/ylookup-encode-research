"""Harness v6: evidence-based cascade. One task = attempt, verify, escalate, select.

Stage 1  champion attempt: baseline values-only prompt + baseline serialiser +
         h2 write path — byte-identical to the E004 champion configuration.
         Healthy -> done. (Skipped only when the doomed-check proves it
         unwinnable: answer cells outside the 120x30 baseline view, or an
         answer range too large to emit as literal values.)
Stage 2  escalation: coverage serialiser + formula-permitting prompt +
         formula write path.
Stage 3  one repair retry, fed the CONCRETE evidence from the health check
         ("your formula in C6 evaluates to #N/A after recalculation").

Selection: the attempt with the fewest hard failures wins; ties go to the
earliest stage, so the champion artifact is never displaced by an
equally-or-less-healthy challenger. Worst case per task == champion output.

Health signals are golden-free (see health.py). The optional champion cache
reuses a stored response ONLY when the freshly built champion prompt is
byte-identical to the cached trace's prompt — the experiment's matched
control; production runs simply have no cache.
"""

import asyncio
import json
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baseline"))

from common import SYSTEM_PROMPT as CHAMPION_SYSTEM_PROMPT
from common import build_prompt as champion_build_prompt
from openpyxl.utils.cell import coordinate_to_tuple

import openpyxl

from inference import health as health_mod
from inference.parse import parse_answer_lenient
from inference.predict import SYSTEM_PROMPT_FORMULAS
from inference.serialize import build_prompt as coverage_build_prompt
from inference.write import write_output
from sb import answer_cells

HARNESS_VERSION = "h7-cascade-fv"
BASELINE_VIEW_ROWS, BASELINE_VIEW_COLS = 120, 30
# Above every answer-range size the champion configuration has ever passed
# (max known pass: 200 cells). Below this, stage 1 always gets its chance.
LARGE_ANSWER_CELLS = 300
_RECALC_SEMAPHORE = asyncio.Semaphore(3)  # concurrent headless LibreOffice instances

REPAIR_HINT = (
    "\n\nYour previous answer had problems detected by automatic validation:\n{evidence}\n"
    "Produce a corrected answer. If a formula caused an error, fix it or replace it with "
    "a direct literal value. Reply with the same JSON shape as before."
)


@dataclass
class Attempt:
    stage: str
    path: Path
    trace: dict
    report: object  # HealthReport


def doomed_reason(task: dict) -> str | None:
    """Champion attempt is provably unwinnable: it cannot even see/emit the answer."""
    wb = openpyxl.load_workbook(task["init_xlsx"], read_only=True)
    cells = answer_cells(task, wb)
    wb.close()
    if len(cells) > LARGE_ANSWER_CELLS:
        return f"answer range has {len(cells)} cells (> {LARGE_ANSWER_CELLS})"
    for _sheet, coord in cells:
        row, col = coordinate_to_tuple(coord)[0], coordinate_to_tuple(coord)[1]
        if row > BASELINE_VIEW_ROWS or col > BASELINE_VIEW_COLS:
            return f"answer cell {coord} outside baseline {BASELINE_VIEW_ROWS}x{BASELINE_VIEW_COLS} view"
    return None


def load_cached_response(cache_dir: Path | None, task: dict, champion_prompt: str) -> dict | None:
    """Cached E00x trace reused only on byte-identical prompt (matched control)."""
    if cache_dir is None:
        return None
    trace_path = cache_dir / "traces" / f"{task['id']}.jsonl"
    if not trace_path.exists():
        return None
    cached = json.loads(trace_path.read_text().splitlines()[0])
    if cached.get("prompt") != champion_prompt or not cached.get("response"):
        return None
    return cached


async def _assess(task, path, *, stage, output_tokens, max_tokens, parse_mode):
    async with _RECALC_SEMAPHORE:
        return await asyncio.to_thread(
            health_mod.assess, task, path, stage=stage, output_tokens=output_tokens,
            max_tokens=max_tokens, parse_mode=parse_mode)


async def _run_attempt(complete, task, *, stage, system, user_prompt, path,
                       max_tokens, model, cached=None) -> Attempt:
    # max_tokens is this attempt's own budget: forwarded to sampling AND to the
    # truncation health check, so escalation stages may run with more headroom.
    trace = {"step": None, "model": model, "stage": stage, "cached": bool(cached),
             "prompt": user_prompt, "response": None,
             "input_tokens": None, "output_tokens": None, "latency_ms": None, "error": None}
    started = time.time()
    parse_mode = None
    try:
        if cached:
            text = cached["response"]
            trace["input_tokens"], trace["output_tokens"] = cached.get("input_tokens"), cached.get("output_tokens")
        else:
            text, trace["input_tokens"], trace["output_tokens"] = await complete(system, user_prompt, max_tokens)
        trace["response"] = text
        answer, parse_mode = parse_answer_lenient(text)
        await asyncio.to_thread(write_output, task, answer, path)
    except Exception as e:
        shutil.copy(task["init_xlsx"], path)
        trace["error"] = f"{type(e).__name__}: {e}"[:500]
    trace["latency_ms"] = int((time.time() - started) * 1000)
    report = await _assess(task, path, stage=stage, output_tokens=trace["output_tokens"],
                           max_tokens=max_tokens, parse_mode=parse_mode)
    trace["health"] = report.summary()
    return Attempt(stage=stage, path=path, trace=trace, report=report)


def _evidence(report) -> str:
    lines = []
    if report.truncated:
        lines.append("- the reply was cut off at the token limit before it finished")
    if report.parse_failed:
        lines.append("- no valid JSON answer could be extracted from the reply")
    for issue in report.static_issues[:3]:
        lines.append(f"- formula problem: {issue}")
    if report.recalc_errors:
        lines.append(f"- after recalculation, {report.recalc_errors} answer cell(s) "
                     f"contain Excel error values such as #N/A or #NAME?")
    return "\n".join(lines) or "- the answer appears incomplete"


async def run_cascade_task(complete, task: dict, work_dir: Path, *,
                           max_tokens: int, model: str, cache_dir: Path | None,
                           escalation_max_tokens: int | None = None) -> tuple[Path, list[dict], str]:
    """Returns (best_output_path, trace_records, status_string)."""
    esc_tokens = escalation_max_tokens or max_tokens
    attempts: list[Attempt] = []
    tmp = work_dir / task["id"]
    tmp.mkdir(parents=True, exist_ok=True)

    reason = doomed_reason(task)
    if reason is None:
        champion_prompt = champion_build_prompt(task)
        cached = load_cached_response(cache_dir, task, champion_prompt)
        attempts.append(await _run_attempt(
            complete, task, stage="champion", system=CHAMPION_SYSTEM_PROMPT,
            user_prompt=champion_prompt, path=tmp / "champion.xlsx",
            max_tokens=max_tokens, model=model, cached=cached))

    if not attempts or not attempts[-1].report.healthy:
        formula_prompt = coverage_build_prompt(task)
        escalation = await _run_attempt(
            complete, task, stage="formula", system=SYSTEM_PROMPT_FORMULAS,
            user_prompt=formula_prompt, path=tmp / "formula.xlsx",
            max_tokens=esc_tokens, model=model)
        escalation.trace["gate"] = reason or "champion attempt unhealthy"
        attempts.append(escalation)

        if not escalation.report.healthy:
            repair_prompt = formula_prompt + REPAIR_HINT.format(evidence=_evidence(escalation.report))
            attempts.append(await _run_attempt(
                complete, task, stage="repair", system=SYSTEM_PROMPT_FORMULAS,
                user_prompt=repair_prompt, path=tmp / "repair.xlsx",
                max_tokens=esc_tokens, model=model))

    best = min(attempts, key=lambda a: a.report.hard_failures)  # min is stable: ties -> earliest stage
    traces = []
    for step, attempt in enumerate(attempts, 1):
        attempt.trace["step"] = step
        attempt.trace["selected"] = attempt is best
        traces.append(attempt.trace)
    status = "ok" if best.report.healthy else f"unhealthy: hard_failures={best.report.hard_failures}"
    if best.trace["error"]:
        status = f"error: {best.trace['error']}"[:200]
    return best.path, traces, status
