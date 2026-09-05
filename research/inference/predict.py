"""Harness v3 Tinker prediction: baseline pipeline + coverage serialisation +
lenient parse + faithful write. One model call per task, values not formulas.

    uv run inference/predict.py --out-dir ../experiments/X --base-model Qwen/Qwen3.8-27B \
        --ids 13-1 --concurrency 12 --max-tokens 24576

Plumbing mirrors baseline/tinker_predict.py + baseline/common.py (same trace,
predictions, run.log formats) so outputs stay contract-compatible.
"""

import argparse
import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baseline"))

import tinker
from common import FORMAT_HINT, append_jsonl, load_env, log, parse_ids, prepare_out_dir, selected_tasks
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.parse import parse_answer_lenient
from inference.serialize import build_prompt
from inference.write import write_output
from sb import DEFAULT_DATASET

HARNESS_VERSION = "h4-formulas"

SYSTEM_PROMPT_FORMULAS = (
    "You are a spreadsheet expert. You get a serialized workbook and a user instruction. "
    "Determine what the answer range must contain after the instruction is applied. "
    "Return one entry per cell in the answer range. Use null for cells that must be empty. "
    "Each value may be either a literal value or an Excel formula string starting with '='. "
    "Prefer a formula whenever it is more reliable than mental arithmetic: aggregations or "
    "lookups over many rows, calculations over data the workbook view shows only a sample of "
    "(formulas operate on the FULL data, including omitted rows), or large answer ranges. "
    "Prefer literal values for short answers you can read or compute directly and exactly. "
    "Use classic Excel functions (SUM, SUMIFS, COUNTIFS, INDEX, MATCH, VLOOKUP, IF, TEXT) "
    "when possible; they are the most portable. Formulas are recalculated before grading, "
    "so their computed values are what counts."
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--dataset-dir", default=str(DEFAULT_DATASET))
    p.add_argument("--ids")
    p.add_argument("--base-model", required=True)
    p.add_argument("--model-path")
    p.add_argument("--concurrency", type=int, default=12)
    p.add_argument("--max-tokens", type=int, default=24576)
    return p.parse_args()


async def predict_task(complete, model: str, task: dict, out_dir: Path) -> str:
    out = out_dir / "outputs" / f"{task['id']}.xlsx"
    trace = {"step": 1, "model": model, "prompt": None, "response": None,
             "input_tokens": None, "output_tokens": None, "latency_ms": None, "error": None}
    started = time.time()
    try:
        trace["prompt"] = build_prompt(task)
        text, trace["input_tokens"], trace["output_tokens"] = await complete(trace["prompt"])
        trace["response"] = text
        answer, mode = parse_answer_lenient(text)
        write_output(task, answer, out)
        status = "ok" if mode == "strict" else "ok (salvaged)"
    except Exception as e:
        shutil.copy(task["init_xlsx"], out)
        trace["error"] = f"{type(e).__name__}: {e}"[:500]
        status = f"error: {e}"[:200]
    trace["latency_ms"] = int((time.time() - started) * 1000)
    append_jsonl(out_dir / "traces" / f"{task['id']}.jsonl", trace)
    append_jsonl(out_dir / "predictions.jsonl",
                 {"id": task["id"], "output": f"outputs/{task['id']}.xlsx", "status": status})
    return status


async def main():
    load_env()
    args = parse_args()
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model=args.base_model, model_path=args.model_path)
    renderer = renderers.get_renderer(get_recommended_renderer_name(args.base_model), get_tokenizer(args.base_model))
    params = types.SamplingParams(max_tokens=args.max_tokens, temperature=0, stop=renderer.get_stop_sequences())

    async def complete(prompt: str):
        messages = [{"role": "system", "content": SYSTEM_PROMPT_FORMULAS}, {"role": "user", "content": prompt + FORMAT_HINT}]
        model_input = renderer.build_generation_prompt(messages)
        response = await sampler.sample_async(prompt=model_input, num_samples=1, sampling_params=params)
        tokens = response.sequences[0].tokens
        content = renderer.parse_response(tokens)[0]["content"]
        if not isinstance(content, str):
            content = "".join(part.get("text", "") for part in content if part.get("type") == "text")
        return content, model_input.length, len(tokens)

    tasks = selected_tasks(Path(args.dataset_dir), parse_ids(args.ids))
    out_dir = Path(args.out_dir)
    prepare_out_dir(out_dir)
    log(out_dir, f"harness {HARNESS_VERSION}  model {args.model_path or args.base_model}  tasks {len(tasks)}")
    semaphore = asyncio.Semaphore(args.concurrency)

    async def run_one(task: dict) -> None:
        async with semaphore:
            status = await predict_task(complete, args.model_path or args.base_model, task, out_dir)
        log(out_dir, f"{task['id']:<8} {status}")

    await asyncio.gather(*(run_one(task) for task in tasks))


if __name__ == "__main__":
    asyncio.run(main())
