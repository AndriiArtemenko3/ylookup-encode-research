"""PHASE 3 H10 execution-agent TRAIN mechanism probe (preregistered ids).

    uv run training/h10_probe.py

Preregistered ids (from residual audit's code-execution class, before any
probe result; overlap with the patch probe avoided; includes the whales):
17-35, 23-24, 24-23, 41-47, 297-42, 408-5, 455-35, 80-42, 118-50, 146-49.

Per task: build the workbook manifest -> model writes a python/openpyxl
program (one repair on failure, fed stdout/stderr) -> sandboxed execution on
a COPY -> official verifier score (train-side). Tool failures reported
separately from reasoning failures.
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import tinker
from common import load_env
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.retry import with_backoff
from sb import load_dataset
from tools.pyexec import build_exec_prompt, build_repair_prompt, extract_code, run_code
from tools.workbook import build_manifest
from training.reward import compute_reward

IDS = ["17-35", "23-24", "24-23", "41-47", "297-42", "408-5", "455-35", "80-42", "118-50", "146-49"]


async def main():
    load_env()
    tasks = {t["id"]: t for t in load_dataset()}
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model="Qwen/Qwen3.8-27B", model_path=None)
    renderer = renderers.get_renderer(get_recommended_renderer_name("Qwen/Qwen3.8-27B"),
                                      get_tokenizer("Qwen/Qwen3.8-27B"))
    params = types.SamplingParams(max_tokens=16384, temperature=0, stop=renderer.get_stop_sequences())

    async def ask(prompt):
        messages = [{"role": "system", "content":
                     "You are an expert spreadsheet engineer. Reply with exactly one ```python code block."},
                    {"role": "user", "content": prompt}]
        mi = renderer.build_generation_prompt(messages)
        resp = await with_backoff(lambda: sampler.sample_async(prompt=mi, num_samples=1, sampling_params=params))
        content = renderer.parse_response(resp.sequences[0].tokens)[0]["content"]
        if not isinstance(content, str):
            content = "".join(p.get("text", "") for p in content if p.get("type") == "text")
        return content

    rows = []
    for tid in IDS:
        task = tasks[tid]
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            shutil.copy(task["init_xlsx"], tdir / "input.xlsx")
            manifest = build_manifest(task["init_xlsx"])
            prompt = build_exec_prompt(task["instruction"], json.dumps(manifest)[:8000],
                                       task["answer_position"], task.get("answer_sheet"))
            code = extract_code(await ask(prompt))
            res = run_code(code, tdir, timeout=90)
            attempt = 1
            if not res["ok"]:
                repair = build_repair_prompt(code, res["stdout"][-2000:], res["stderr"][-3000:], res["stderr"][-3000:])
                code = extract_code(await ask(repair))
                res = run_code(code, tdir, timeout=90)
                attempt = 2
            if not res["ok"]:
                rows.append((tid, "TOOL-FAIL", attempt, res["stderr"][:80].replace("\n", " "), None))
                continue
            reward, item = compute_reward(task, tdir / "output.xlsx", td)
            rows.append((tid, "PASS" if item.get("pass") else "fail", attempt,
                         f"{item.get('correct')}/{item.get('cells')}", round(reward, 3)))

    print(f"{'task':<8} {'outcome':<10} {'try':<4} {'cells':<14} reward")
    for r in rows:
        print(f"{r[0]:<8} {r[1]:<10} {r[2]:<4} {str(r[3]):<14} {r[4]}")
    n_pass = sum(1 for r in rows if r[1] == "PASS")
    n_tool = sum(1 for r in rows if r[1] == "TOOL-FAIL")
    print(f"\nconversions {n_pass}/{len(rows)} | tool failures {n_tool} | reasoning failures {len(rows)-n_pass-n_tool}")


if __name__ == "__main__":
    asyncio.run(main())
