"""H11 adaptive-ladder TRAIN probe per docs/H11_LADDER_PLAN.md (frozen).

    uv run training/h11_probe.py

Runs the h8 cascade (24k champion / 32k escalation) on the preregistered
train truncation-class ids, then applies the frozen 40k rung only where the
plan's conditions (cap-hit AND coverage-progress AND context-fit) hold.
Scores train-side with the official verifier.
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
from common import FORMAT_HINT, load_env
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.cascade import run_cascade_task
from inference.parse import parse_answer_lenient
from inference.predict import SYSTEM_PROMPT_FORMULAS
from inference.retry import with_backoff
from inference.serialize import build_prompt as coverage_build_prompt
from inference.write import write_output
from sb import load_dataset
from training.reward import compute_reward, train_ids

FINAL_RUNG = 40960
CTX = 65536


def preregistered_ids():
    audit = json.load(open(RESEARCH.parent / "experiments" / "E009-residual-audit.json"))
    rows = {r["id"]: r for r in audit["rows"]}
    tr = train_ids()
    out = []
    for tid in sorted(rows):
        if tid not in tr:
            continue
        tf = RESEARCH.parent / "experiments" / "E009-champion-400" / "traces" / f"{tid}.jsonl"
        if not tf.exists():
            continue
        lines = [json.loads(l) for l in tf.read_text().splitlines()]
        sel = next((t for t in lines if t.get("selected")), lines[-1])
        if (sel.get("output_tokens") or 0) >= 24576:
            out.append(tid)
    return out[:8]


def n_cells(response):
    try:
        a, _ = parse_answer_lenient(response)
        return len(a.cells), a
    except Exception:
        return 0, None


async def main():
    load_env()
    ids = preregistered_ids()
    print("preregistered H11 ids:", ids)
    tasks = {t["id"]: t for t in load_dataset()}
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model="Qwen/Qwen3.8-27B", model_path=None)
    renderer = renderers.get_renderer(get_recommended_renderer_name("Qwen/Qwen3.8-27B"),
                                      get_tokenizer("Qwen/Qwen3.8-27B"))
    stops = renderer.get_stop_sequences()

    async def complete(system, user_prompt, max_tokens):
        params = types.SamplingParams(max_tokens=max_tokens, temperature=0, stop=stops)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user_prompt + FORMAT_HINT}]
        mi = renderer.build_generation_prompt(messages)
        resp = await with_backoff(lambda: sampler.sample_async(prompt=mi, num_samples=1, sampling_params=params))
        toks = resp.sequences[0].tokens
        content = renderer.parse_response(toks)[0]["content"]
        if not isinstance(content, str):
            content = "".join(p.get("text", "") for p in content if p.get("type") == "text")
        return content, mi.length, len(toks)

    rows = []
    for tid in ids:
        task = tasks[tid]
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            best, traces, status = await run_cascade_task(
                complete, task, work, max_tokens=24576, model="Qwen/Qwen3.8-27B",
                cache_dir=None, escalation_max_tokens=32768)
            r32, item32 = compute_reward(task, best, td)
            champ = next((t for t in traces if t.get("stage") == "champion"), None)
            esc = [t for t in traces if t.get("stage") in ("formula", "repair")]
            cov24 = n_cells(champ["response"])[0] if champ and champ.get("response") else 0
            last_esc = esc[-1] if esc else None
            cov32 = n_cells(last_esc["response"])[0] if last_esc and last_esc.get("response") else 0
            capped32 = bool(last_esc and (last_esc.get("output_tokens") or 0) >= 32768)
            prompt_len = (last_esc or champ or {}).get("input_tokens") or 0
            stop_reason, r40 = "healthy" if item32.get("pass") else "budget_or_content", None
            if not item32.get("pass") and capped32 and cov32 > cov24 and prompt_len + FINAL_RUNG + 512 <= CTX:
                text, _pi, ot = await complete(SYSTEM_PROMPT_FORMULAS, coverage_build_prompt(task), FINAL_RUNG)
                nc, answer = n_cells(text)
                if answer:
                    out40 = work / "rung40.xlsx"
                    write_output(task, answer, out40)
                    r40v, item40 = compute_reward(task, out40, td)
                    if (item40.get("correct") or 0) > (item32.get("correct") or 0):
                        item32, r32 = item40, r40v
                    r40 = f"{item40.get('correct')}/{item40.get('cells')}{' PASS' if item40.get('pass') else ''}"
                    stop_reason = "solved" if item40.get("pass") else "budget_exhausted" if ot >= FINAL_RUNG else "content"
            elif not item32.get("pass") and capped32 and cov32 <= cov24:
                stop_reason = "reasoning_loop"
            rows.append((tid, f"{item32.get('correct')}/{item32.get('cells')}",
                         "PASS" if item32.get("pass") else "fail", cov24, cov32, r40, stop_reason))

    print(f"{'task':<8} {'cells':<12} {'out':<5} cov24 cov32 rung40         stop")
    for r in rows:
        print(f"{r[0]:<8} {r[1]:<12} {r[2]:<5} {r[3]:<5} {r[4]:<5} {str(r[5]):<14} {r[6]}")
    print(f"\nconversions: {sum(1 for r in rows if r[2]=='PASS')}/{len(rows)}")


if __name__ == "__main__":
    asyncio.run(main())
