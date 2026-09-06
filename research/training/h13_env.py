"""H13A: SpreadsheetBench online-RLVR environment for tinker_cookbook.rl.

Single-turn Env: routed observation (finalist's deterministic golden-free
routing) -> current-policy completion -> parse -> h2 write -> recalc if
formulas -> official score_task on the TRAIN golden -> R0 reward.
The model never sees golden content; the verifier runs only after a candidate
workbook exists. TRAIN-split enforcement via training.reward.train_ids.
"""

import json
import tempfile
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import chz
from common import FORMAT_HINT, SYSTEM_PROMPT
from common import build_prompt as champion_build_prompt
from tinker_cookbook import renderers
from tinker_cookbook.rl.types import (Env, EnvGroupBuilder, RLDataset, RLDatasetBuilder, StepResult)

import tinker

from evaluate import score_task
from inference.cascade import doomed_reason
from inference.parse import parse_answer_lenient
from inference.predict import SYSTEM_PROMPT_FORMULAS
from inference.serialize import build_prompt as coverage_build_prompt
from inference.write import write_output
from sb import load_dataset, recalculate
from sb import answer_ranges as sb_answer_ranges
from training.reward import train_ids

ROLLOUTS = RESEARCH.parent / "experiments" / "F1v2-rollouts-reasoning-preserved" / "rollouts"


def routed_messages(task):
    """Finalist-equivalent deterministic routing (golden-free)."""
    sheets = {s for s, _r in sb_answer_ranges(task)}
    clause = ""
    if len(sheets) > 1:
        clause = ("\n\nIMPORTANT: the answer range spans multiple sheets. Write every cell "
                  "address sheet-qualified as 'SheetName!CELL'.")
    if doomed_reason(task) is not None:
        system, user = SYSTEM_PROMPT_FORMULAS, coverage_build_prompt(task) + clause
        route = "coverage"
    else:
        system, user = SYSTEM_PROMPT, champion_build_prompt(task) + clause
        route = "champion"
    return system, user + FORMAT_HINT, route


class SpreadsheetEnv(Env):
    def __init__(self, task_id: str, renderer_name: str, model_name: str):
        self.task_id = task_id
        self.renderer_name = renderer_name
        self.model_name = model_name
        self._renderer = None
        self._task = None

    @property
    def renderer(self):
        if self._renderer is None:
            from tinker_cookbook.model_info import get_recommended_renderer_name
            from tinker_cookbook.tokenizer_utils import get_tokenizer
            name = self.renderer_name or get_recommended_renderer_name(self.model_name)
            self._renderer = renderers.get_renderer(name, get_tokenizer(self.model_name))
        return self._renderer

    @property
    def task(self):
        if self._task is None:
            self._task = next(t for t in load_dataset() if t["id"] == self.task_id)
        return self._task

    async def initial_observation(self):
        system, user, _route = routed_messages(self.task)
        convo = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        return self.renderer.build_generation_prompt(convo), self.renderer.get_stop_sequences()

    async def step(self, action, *, extra=None) -> StepResult:
        message, termination = self.renderer.parse_response(action)
        content = renderers.get_text_content(message)
        metrics = {"completion_tokens": len(action), "parse_valid": 0.0,
                   "exact_pass": 0.0, "cell_accuracy": 0.0}
        reward = -0.1
        try:
            answer, _mode = parse_answer_lenient(content)
            metrics["parse_valid"] = 1.0
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "cand.xlsx"
                write_output(self.task, answer, out)
                if any(isinstance(c.value, str) and str(c.value).startswith("=") for c in answer.cells):
                    out = recalculate(out, td)
                item = score_task(self.task, str(out), False, td)
            if item.get("status") == "graded":
                cells = item.get("cells") or 0
                acc = (item.get("correct") or 0) / cells if cells else 0.0
                metrics["cell_accuracy"] = acc
                if item.get("pass"):
                    reward, metrics["exact_pass"] = 1.0, 1.0
                else:
                    reward = 0.2 * acc
        except Exception:
            pass
        return StepResult(reward=reward, episode_done=True,
                          next_observation=tinker.ModelInput.empty(),
                          next_stop_condition=self.renderer.get_stop_sequences(),
                          metrics=metrics)


class SpreadsheetGroupBuilder(EnvGroupBuilder):
    def __init__(self, task_id: str, group_size: int, renderer_name: str, model_name: str):
        self.task_id = task_id
        self.group_size = group_size
        self.renderer_name = renderer_name
        self.model_name = model_name

    async def make_envs(self):
        return [SpreadsheetEnv(self.task_id, self.renderer_name, self.model_name)
                for _ in range(self.group_size)]

    def logging_tags(self):
        return ["spreadsheet"]


class SpreadsheetDataset(RLDataset):
    def __init__(self, task_ids, groups_per_batch, group_size, n_batches, renderer_name, model_name):
        self.task_ids = task_ids
        self.groups_per_batch = groups_per_batch
        self.group_size = group_size
        self.n_batches = n_batches
        self.renderer_name = renderer_name
        self.model_name = model_name

    def __len__(self):
        return self.n_batches

    def get_batch(self, index):
        start = (index * self.groups_per_batch) % len(self.task_ids)
        chosen = [self.task_ids[(start + j) % len(self.task_ids)] for j in range(self.groups_per_batch)]
        return [SpreadsheetGroupBuilder(t, self.group_size, self.renderer_name, self.model_name)
                for t in chosen]


def frozen_task_list(max_cap_tokens=24576):
    """FROZEN selection per plan: boundary groups, minus output-bound and
    msheet-bug tasks. Deterministic order, seed 42 shuffle."""
    import random
    exclude = {"283-32", "156-14", "170-13", "141-20", "302-1"}
    tids = []
    for d in sorted(ROLLOUTS.iterdir()):
        if not (d / "prompt_tokens.json").exists() or d.name in exclude:
            continue
        recs = [json.loads(f.read_text()) for f in sorted(d.glob("[0-9]*.json"))]
        if not recs:
            continue
        passes = sum(1 for r in recs if (r.get("score") or {}).get("pass"))
        accs = [((r.get("score") or {}).get("correct") or 0) / max((r.get("score") or {}).get("cells") or 1, 1)
                for r in recs]
        toks = [r.get("completion_tokens_n") or 0 for r in recs]
        if toks and min(toks) >= max_cap_tokens:  # every candidate capped: output-bound
            continue
        if (0 < passes < len(recs)) or (passes == 0 and max(accs) - min(accs) >= 0.10):
            tids.append(d.name)
    rng = random.Random(42)
    rng.shuffle(tids)
    assert all(t in train_ids() for t in tids)
    return tids


@chz.chz
class SpreadsheetDatasetBuilder(RLDatasetBuilder):
    model_name: str = "Qwen/Qwen3.8-27B"
    renderer_name: str = ""
    group_size: int = 8
    groups_per_batch: int = 4
    n_batches: int = 20

    async def __call__(self):
        tids = frozen_task_list()
        (RESEARCH.parent / "experiments" / "H13A-online-rlvr").mkdir(parents=True, exist_ok=True)
        (RESEARCH.parent / "experiments" / "H13A-online-rlvr" / "frozen_tasks.json").write_text(
            json.dumps({"task_ids": tids, "n": len(tids)}))
        return (SpreadsheetDataset(tids, self.groups_per_batch, self.group_size,
                                   self.n_batches, self.renderer_name, self.model_name), None)
