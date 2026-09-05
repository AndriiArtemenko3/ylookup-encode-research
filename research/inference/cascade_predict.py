"""CLI for the h6 cascade harness (see cascade.py).

    uv run inference/cascade_predict.py --out-dir ../experiments/X \
        --base-model Qwen/Qwen3.8-27B --ids 13-1 --concurrency 12 \
        [--champion-cache ../experiments/E002-maxtokens-24k-dev]

--champion-cache enables the matched-control mode: champion attempts whose
freshly built prompt is byte-identical to the cached trace's prompt reuse the
stored response (zero tokens, zero sampling noise). Omit it for production /
final runs — identical code path, everything sampled live.

Writes the standard contract: predictions.jsonl, outputs/<id>.xlsx,
traces/<id>.jsonl (one line per attempt, with stage/cached/health/selected
fields), run.log.
"""

import argparse
import asyncio
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baseline"))

import tinker
from common import FORMAT_HINT, append_jsonl, load_env, log, parse_ids, prepare_out_dir, selected_tasks
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.cascade import HARNESS_VERSION, run_cascade_task
from sb import DEFAULT_DATASET


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--dataset-dir", default=str(DEFAULT_DATASET))
    p.add_argument("--ids")
    p.add_argument("--base-model", required=True)
    p.add_argument("--model-path")
    p.add_argument("--concurrency", type=int, default=12)
    p.add_argument("--max-tokens", type=int, default=24576)
    p.add_argument("--escalation-max-tokens", type=int, default=32768,
                   help="budget for formula/repair attempts (champion stage keeps --max-tokens)")
    p.add_argument("--champion-cache", help="experiment dir whose traces seed byte-identical champion attempts")
    return p.parse_args()


async def main():
    load_env()
    args = parse_args()
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model=args.base_model, model_path=args.model_path)
    renderer = renderers.get_renderer(get_recommended_renderer_name(args.base_model), get_tokenizer(args.base_model))
    stops = renderer.get_stop_sequences()
    model = args.model_path or args.base_model

    async def complete(system: str, user_prompt: str, max_tokens: int):
        params = types.SamplingParams(max_tokens=max_tokens, temperature=0, stop=stops)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user_prompt + FORMAT_HINT}]
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
    work_dir = out_dir / "attempts"
    cache_dir = Path(args.champion_cache) if args.champion_cache else None
    log(out_dir, f"harness {HARNESS_VERSION}  model {model}  tasks {len(tasks)}"
                 f"  cache={'on' if cache_dir else 'off'}")
    semaphore = asyncio.Semaphore(args.concurrency)

    async def run_one(task: dict) -> None:
        async with semaphore:
            try:
                best_path, traces, status = await run_cascade_task(
                    complete, task, work_dir, max_tokens=args.max_tokens,
                    model=model, cache_dir=cache_dir,
                    escalation_max_tokens=args.escalation_max_tokens)
                shutil.copy(best_path, out_dir / "outputs" / f"{task['id']}.xlsx")
            except Exception as e:
                shutil.copy(task["init_xlsx"], out_dir / "outputs" / f"{task['id']}.xlsx")
                traces = [{"step": 1, "model": model, "stage": "cascade-crash", "prompt": None,
                           "response": None, "input_tokens": None, "output_tokens": None,
                           "latency_ms": None, "error": f"{type(e).__name__}: {e}"[:500]}]
                status = f"error: {e}"[:200]
            for record in traces:
                append_jsonl(out_dir / "traces" / f"{task['id']}.jsonl", record)
            append_jsonl(out_dir / "predictions.jsonl",
                         {"id": task["id"], "output": f"outputs/{task['id']}.xlsx", "status": status})
        stages = "+".join(t.get("stage", "?") + ("(c)" if t.get("cached") else "") for t in traces)
        log(out_dir, f"{task['id']:<8} {status[:60]}  [{stages}]")

    await asyncio.gather(*(run_one(task) for task in tasks))
    shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
