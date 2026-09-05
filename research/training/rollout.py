"""Group rollouts on the TRAIN split for rejection-sampling SFT / RLVR.

    uv run training/rollout.py --out-dir ../experiments/F1-rollouts \
        --base-model Qwen/Qwen3.8-27B --group-size 4 --temperature 0.7 \
        [--ids 13-1,...] [--limit 40]

For each train task: sample `group_size` completions at exploration
temperature through the frozen champion value-path prompt (baseline
SYSTEM_PROMPT + baseline serialisation), write each candidate workbook via the
h2 write path, and score it with training.reward (official scorer inside).
Inference-time behaviour is untouched: this script exists only to produce
(prompt, response, reward) records under rollouts/<task>/<k>.json.

Exploration temperature is deliberate: at temperature 0 a group collapses to
near-identical completions and group-relative advantages vanish. Evaluation of
any resulting checkpoint runs at temperature 0 through the normal harness.

NOT launched automatically — Phase F requires explicit spend approval.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import tinker
from common import FORMAT_HINT, SYSTEM_PROMPT, build_prompt, load_env, parse_ids
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.parse import parse_answer_lenient
from inference.write import write_output
from sb import load_dataset
from training.reward import compute_reward, train_ids


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", required=True)
    p.add_argument("--base-model", required=True)
    p.add_argument("--model-path")
    p.add_argument("--ids", help="subset of train ids (default: whole train split)")
    p.add_argument("--limit", type=int, help="first N train tasks only")
    p.add_argument("--group-size", type=int, default=4)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=24576)
    p.add_argument("--concurrency", type=int, default=12, help="concurrent samples (task x group)")
    return p.parse_args()


async def main():
    load_env()
    args = parse_args()
    allowed = train_ids()
    wanted = parse_ids(args.ids) or allowed
    tasks = [t for t in load_dataset() if t["id"] in allowed and t["id"] in wanted]
    if args.limit:
        tasks = tasks[:args.limit]
    out_dir = Path(args.out_dir)
    (out_dir / "rollouts").mkdir(parents=True, exist_ok=True)

    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model=args.base_model, model_path=args.model_path)
    renderer = renderers.get_renderer(get_recommended_renderer_name(args.base_model), get_tokenizer(args.base_model))
    params = types.SamplingParams(max_tokens=args.max_tokens, temperature=args.temperature,
                                  stop=renderer.get_stop_sequences())
    semaphore = asyncio.Semaphore(args.concurrency)
    reward_lock = asyncio.Semaphore(3)  # concurrent LibreOffice recalcs

    async def one_rollout(task, k):
        user = build_prompt(task)
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user + FORMAT_HINT}]
        model_input = renderer.build_generation_prompt(messages)
        record = {"task_id": task["id"], "k": k, "temperature": args.temperature,
                  "prompt": user, "response": None, "reward": None, "score": None, "error": None}
        started = time.time()
        try:
            async with semaphore:
                response = await sampler.sample_async(prompt=model_input, num_samples=1, sampling_params=params)
            tokens = response.sequences[0].tokens
            content = renderer.parse_response(tokens)[0]["content"]
            if not isinstance(content, str):
                content = "".join(p.get("text", "") for p in content if p.get("type") == "text")
            record["response"] = content
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "cand.xlsx"
                try:
                    answer, _mode = parse_answer_lenient(content)
                    await asyncio.to_thread(write_output, task, answer, out)
                except Exception as e:
                    shutil.copy(task["init_xlsx"], out)
                    record["error"] = f"{type(e).__name__}: {e}"[:200]
                async with reward_lock:
                    reward, item = await asyncio.to_thread(compute_reward, task, out, td)
            record["reward"] = round(reward, 4)
            record["score"] = {key: item.get(key) for key in ("status", "pass", "cells", "correct")}
        except Exception as e:
            record["error"] = f"{type(e).__name__}: {e}"[:300]
            record["reward"] = -0.1
        record["latency_ms"] = int((time.time() - started) * 1000)
        task_dir = out_dir / "rollouts" / task["id"]
        task_dir.mkdir(exist_ok=True)
        (task_dir / f"{k}.json").write_text(json.dumps(record, ensure_ascii=False))
        return record

    async def one_task(task):
        records = await asyncio.gather(*(one_rollout(task, k) for k in range(args.group_size)))
        rewards = [r["reward"] for r in records]
        n_pass = sum(1 for r in records if (r["score"] or {}).get("pass"))
        line = {"task_id": task["id"], "rewards": rewards, "passes": n_pass, "group": args.group_size}
        with (out_dir / "groups.jsonl").open("a") as f:
            f.write(json.dumps(line) + "\n")
        print(f"{task['id']:<8} passes {n_pass}/{args.group_size}  rewards {rewards}", flush=True)

    for task in tasks:  # tasks sequential, samples within a task parallel
        await one_task(task)


if __name__ == "__main__":
    asyncio.run(main())
