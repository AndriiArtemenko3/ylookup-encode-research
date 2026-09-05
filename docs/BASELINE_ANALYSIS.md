# Untouched baseline analysis

What the starter baseline does, cited from source. Nothing here is inferred.
The baseline is preserved as-is (`research/baseline/`) to give E000 a clean
reference point before any optimisation.

## Pipeline shape

One model call per task, no tools, no retries, values-not-formulas.
Shared plumbing in `research/baseline/common.py`; two entry points:

- `baseline/llm_predict.py` — OpenRouter via pydantic-ai
- `baseline/tinker_predict.py` — Tinker base model or fine-tuned sampler checkpoint

## Workbook serialisation — `sb.serialize_workbook` (research/sb.py:151)

- `openpyxl.load_workbook(path, data_only=True)`: the model sees **cached
  values only, never formulas**. A formula cell with no cached value appears
  empty.
- Truncated to **120 rows × 30 columns per sheet** (`max_rows=120,
  max_cols=30`), with a header noting real dimensions: `### Sheet: <title>
  (showing RxC of RxC)`.
- Tab-separated grid with row numbers and column letters. Every worksheet is
  included. `None` renders as empty string; everything else via `str()`.
- No cell formatting, number formats, merged-cell info, or data-validation
  info is conveyed.

## Prompt — `common.build_prompt` (baseline/common.py:62) + `common.SYSTEM_PROMPT` (baseline/common.py:21)

- System: "spreadsheet expert", compute **final values** for the answer range,
  one entry per cell, `null` for empty, "plain values, not formulas".
- User: `## Instruction` (forum text) + `## Workbook` (serialisation above) +
  `## Answer range` (sheet name or "active sheet", plus `answer_position`).
- Tinker path appends `common.FORMAT_HINT` (baseline/common.py:27) demanding
  JSON only: `{"cells": [{"cell": "B6", "value": 42}, ...]}`.

## What the model must output — `common.SpreadsheetAnswer` (baseline/common.py:38)

`{"cells": [{"cell": str, "value": str|int|float|bool|null}]}`. The LLM path
enforces this as pydantic-ai structured output; the Tinker path parses the
first `{...}` block from raw text (`common.parse_answer`, baseline/common.py:70),
stripping `<think>...</think>` first.

## How answers are written — `common.write_output` (baseline/common.py:79)

Copies the init workbook, then writes ONLY returned cells whose coordinates
fall inside the graded `answer_cells` range (sb.py:64); anything else the model
returns is silently dropped. Values are written as-is (no type coercion).
Sheet resolution: named answer sheet if present, else the active sheet.

## Error behaviour — `common.predict_task` (baseline/common.py:109)

Any exception (API error, unparseable reply, write failure) ⇒ the **init
workbook is copied as the output** (so the task still produces a file, per the
submission contract), status `error: ...` in `predictions.jsonl`, `error` set
in the single trace line. **No retries anywhere.** One trace line per task in
`traces/<id>.jsonl`; `run.log` mirrors stdout.

## Sampling parameters

| | llm_predict.py | tinker_predict.py |
|---|---|---|
| temperature | 0 (`OpenRouterModelSettings(temperature=0)`, llm_predict.py:32) | 0 (`SamplingParams`, tinker_predict.py:43) |
| max tokens | not set (provider default) | 8192 default (`--max-tokens`, tinker_predict.py:34) |
| concurrency | 4 default (`--concurrency`, llm_predict.py:26) | 4 default (tinker_predict.py:33) |
| default model | `deepseek/deepseek-v3.2` (llm_predict.py:25) | none; `--base-model` required, examples use `Qwen/Qwen3-8B` (tinker_predict.py:4-6,31) |
| stop sequences | n/a | renderer's (`renderer.get_stop_sequences()`) |

`common.prepare_out_dir` (baseline/common.py:90) **deletes and recreates**
`outputs/` and `traces/` and truncates `predictions.jsonl`/`run.log` — raw
baseline runs overwrite their out-dir, which is why our experiment runner wraps
them in fresh `experiments/<id>/` dirs that refuse to be overwritten.

## Scoring (for reference) — `research/evaluate.py` + `research/sb.py`

- Only `answer_position` cells on `answer_sheet` are compared
  (`sb.answer_cells`), after LibreOffice headless recalculation
  (`sb.recalculate`, 180 s timeout per file).
- Normalisation `sb.transform_value` (sb.py:89): numbers → round 2dp;
  datetimes → Excel serial rounded to 0dp; times → `str()[:-3]`; numeric
  strings → float. `values_equal` (sb.py:106) then requires **equal type and
  value**; empty string == None.
- A task with no prediction line or missing file counts as fail and
  contributes its golden cell count as zeros to `cell_accuracy` (evaluate.py:91,135).
- Judges score with `--all` (missing = fail).

## Known baseline limitations (observations only — no changes yet)

- Formulas invisible to the model (data_only=True), yet many instructions
  reference formula logic.
- 120×30 truncation loses data on large sheets; `answer_position` rows beyond
  120 are invisible to the model.
- Values-not-formulas means the model must arithmetic perfectly over a
  text grid; no code execution or validation pass.
- Single shot, no retry on parse failure — every malformed reply is an
  automatic task fail (init workbook rarely matches golden).
