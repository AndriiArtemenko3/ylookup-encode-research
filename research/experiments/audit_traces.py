"""Submission-contract audit for a run's traces. Evaluation-side tool.

    uv run experiments/audit_traces.py ../experiments/E009-champion-400

Checks every traces/<id>.jsonl against the contract and the DQ criteria in
research/SUBMISSION.md:

1. Structure: every line parses; required fields present (step, model, prompt,
   response, input_tokens, output_tokens, latency_ms, error); steps ordered.
2. Coverage: every prediction id has a trace file and vice versa.
3. No lookup smell: prompts never reference golden paths or files.
4. No golden leakage into PROMPTS: for every task, distinctive golden answer
   values (golden cell values that do NOT already appear in the init workbook
   — init-visible values are legitimate input) must not appear verbatim in any
   prompt. Responses are allowed to contain answer values — that is the model
   answering, with its reasoning in the same trace.

Reads golden files (audit side, like the evaluator). Exit code 1 on any finding.
"""

import json
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))

import openpyxl

from sb import load_answer_values, load_dataset

REQUIRED = {"step", "model", "prompt", "response", "input_tokens", "output_tokens", "latency_ms", "error"}


def init_value_pool(task) -> set[str]:
    pool = set()
    wb = openpyxl.load_workbook(task["init_xlsx"], data_only=True, read_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            for v in row:
                if v is not None:
                    pool.add(str(v))
    wb.close()
    return pool


def distinctive_golden_values(task) -> list[str]:
    """Golden answer-cell values not present in the task's own inputs.

    A value that appears in (or inside) any init cell or the instruction is
    legitimate prompt content — prompts are built from exactly those inputs.
    Only values with no input provenance are leakage evidence."""
    try:
        gold = load_answer_values(task["golden_xlsx"], task)
    except Exception:
        return []
    pool = init_value_pool(task)
    pool.add(task["instruction"])
    out = []
    for v in gold.values():
        s = str(v)
        # short/common strings collide by chance; only audit distinctive ones
        if v is not None and len(s) >= 6 and not s.startswith(("0.", "-0.")) \
                and not any(s in entry for entry in pool):
            out.append(s)
    return out


def main():
    exp = Path(sys.argv[1])
    tasks = {str(t["id"]): t for t in load_dataset()}
    predictions = {json.loads(l)["id"] for l in (exp / "predictions.jsonl").read_text().splitlines() if l.strip()}
    findings = []

    trace_files = {p.stem: p for p in (exp / "traces").glob("*.jsonl")}
    for tid in predictions - set(trace_files):
        findings.append(f"{tid}: prediction without trace file")
    for tid in set(trace_files) - predictions:
        findings.append(f"{tid}: trace without prediction line")

    audited = 0
    for tid, path in sorted(trace_files.items()):
        task = tasks.get(tid)
        lines = []
        for i, raw in enumerate(path.read_text().splitlines(), 1):
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                findings.append(f"{tid}: line {i} is not valid JSON")
        for rec in lines:
            missing = REQUIRED - set(rec)
            if missing:
                findings.append(f"{tid}: step {rec.get('step')} missing fields {sorted(missing)}")
            prompt = rec.get("prompt") or ""
            # lookup smell = file/path-shaped references, not the English word
            # appearing inside workbook data (school names, street addresses)
            for marker in ("golden.xlsx", "_golden", "golden_xlsx", "/golden"):
                if marker in prompt.lower():
                    findings.append(f"{tid}: prompt contains path-like reference {marker!r}")
                    break
        if [r.get("step") for r in lines] != list(range(1, len(lines) + 1)):
            findings.append(f"{tid}: steps not sequential")
        if task and task.get("golden_xlsx"):
            prompts = " \n".join((r.get("prompt") or "") for r in lines)
            for value in distinctive_golden_values(task)[:50]:
                if value in prompts:
                    findings.append(f"{tid}: distinctive golden value {value[:40]!r} appears in a PROMPT")
                    break
        audited += 1

    print(f"audited {audited} trace files, {len(predictions)} predictions")
    if findings:
        print(f"\nFINDINGS ({len(findings)}):")
        for f in findings[:40]:
            print(" -", f)
        sys.exit(1)
    print("CLEAN: structure, coverage, no lookup smell, no golden values in prompts")


if __name__ == "__main__":
    main()
