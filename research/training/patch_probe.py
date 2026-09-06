"""PHASE 4 patch-repair TRAIN mechanism probe (preregistered ids inside).

    uv run training/patch_probe.py

For each preregistered near-miss TRAIN task (best rollout candidate <=10 wrong
cells): rebuild the best candidate artifact, derive SUSPICIOUS cells from
generic golden-free evidence only —
  (a) cells where the 4 rollout candidates disagree,
  (b) structural-invariant flags on the artifact —
then issue ONE live patch call (only those cells), merge under the hard
allowlist, and score before/after with the official verifier (train-side).

Measures marginal value beyond H3 by reporting, per task, whether the H3
cascade already fixed it (known from P-H3-train-probe).

Preregistered ids (chosen from residual_analysis before this probe ran):
341-40 (6 empty + 3 float-tie), 496-34 (4 date-text), 32789 (4 off-by-one),
41978 (3 counts), 52305 (10 zeros), 157-4 (21 stable type mismatches).
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import tinker
from common import FORMAT_HINT, SYSTEM_PROMPT, load_env
from common import build_prompt as champion_build_prompt
from tinker import types
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from inference.consensus import agreement_stats
from inference.invariants import structural_defects
from inference.parse import parse_answer_lenient
from inference.patch import apply_patch, build_patch_prompt
from inference.retry import with_backoff
from inference.write import write_output
from sb import load_dataset
from training.reward import compute_reward

IDS = ["341-40", "496-34", "32789", "41978", "52305", "157-4"]
ROLLOUTS = RESEARCH.parent / "experiments" / "F1v2-rollouts-reasoning-preserved" / "rollouts"
H3_ALREADY_FIXED = {"120-24", "398-14", "73-45"}  # from P-H3-train-probe


def candidates_for(tid, task):
    recs = [json.loads(f.read_text()) for f in sorted((ROLLOUTS / tid).glob("[0-9]*.json"))]
    parsed = []
    for r in recs:
        if not r.get("response"):
            continue
        try:
            answer, _ = parse_answer_lenient(r["response"])
            parsed.append((r, answer, {c.cell.upper(): c.value for c in answer.cells}))
        except Exception:
            pass
    best = max(parsed, key=lambda t: (t[0].get("score") or {}).get("correct") or 0, default=None)
    return parsed, best


async def main():
    load_env()
    tasks = {t["id"]: t for t in load_dataset()}
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    sampler = service.create_sampling_client(base_model="Qwen/Qwen3.8-27B", model_path=None)
    renderer = renderers.get_renderer(get_recommended_renderer_name("Qwen/Qwen3.8-27B"),
                                      get_tokenizer("Qwen/Qwen3.8-27B"))
    params = types.SamplingParams(max_tokens=16384, temperature=0, stop=renderer.get_stop_sequences())

    results = []
    for tid in IDS:
        task = tasks[tid]
        parsed, best = candidates_for(tid, task)
        if not best:
            results.append((tid, "no candidate", None, None)); continue
        rec, answer, best_cells = best
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "base.xlsx"
            write_output(task, answer, base)
            r0, item0 = compute_reward(task, base, td)
            # golden-free suspicious cells: candidate disagreement + structural flags
            cell_dicts = [c for _r, _a, c in parsed]
            stats = agreement_stats([{("", k): v for k, v in d.items()} for d in cell_dicts])
            suspicious = set()
            for (s, k), pc in stats["per_cell"].items():
                if pc["distinct"] > 1 or pc["proposals"] < len(cell_dicts):
                    suspicious.add(k)
            defects, flagged = structural_defects(task, base)
            sheet_default = (task.get("answer_sheet") or "").strip("'\"") or None
            wbsheet = sheet_default
            if wbsheet is None:
                import openpyxl
                wb = openpyxl.load_workbook(task["init_xlsx"], read_only=True)
                wbsheet = wb.active.title; wb.close()
            allowed = {(wbsheet.lower(), k) for k in suspicious} | {(s.lower(), c) for s, c in flagged}
            allowed = set(list(allowed)[:24])
            if not allowed:
                results.append((tid, "no suspicious cells", item0, None)); continue
            patch_cells = sorted(allowed)
            prompt = build_patch_prompt(champion_build_prompt(task), patch_cells,
                                        {pc: "candidates disagree or structural flag" for pc in patch_cells})
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt + FORMAT_HINT}]
            mi = renderer.build_generation_prompt(messages)
            resp = await with_backoff(lambda: sampler.sample_async(prompt=mi, num_samples=1, sampling_params=params))
            content = renderer.parse_response(resp.sequences[0].tokens)[0]["content"]
            if not isinstance(content, str):
                content = "".join(p.get("text", "") for p in content if p.get("type") == "text")
            try:
                patch_answer, _ = parse_answer_lenient(content)
            except Exception as e:
                results.append((tid, f"patch parse failed: {e}", item0, None)); continue
            out = Path(td) / "patched.xlsx"
            applied, rejected = apply_patch(base, patch_answer, allowed, out)
            r1, item1 = compute_reward(task, out, td)
            results.append((tid, f"applied={applied} rejected={rejected}", item0, item1))

    print(f"{'task':<8} {'before':>12} {'after':>12}  note")
    for tid, note, i0, i1 in results:
        b = f"{i0['correct']}/{i0['cells']}" if i0 else "-"
        a = f"{i1['correct']}/{i1['cells']}" + (" PASS" if i1 and i1.get("pass") else "") if i1 else "-"
        h3 = " [H3-overlap]" if tid in H3_ALREADY_FIXED else ""
        print(f"{tid:<8} {b:>12} {a:>12}  {note}{h3}")


if __name__ == "__main__":
    asyncio.run(main())
