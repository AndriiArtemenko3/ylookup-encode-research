"""H13C: full-train online-RLVR dataset builder (additive; H13A untouched).

Task universe = ALL 280 frozen TRAIN tasks, uniform seed-42 shuffle, one
coverage pass: 14 batches x 20 groups x K=4 fresh rollouts. Same Env, reward,
routing, renderer as H13A (imported, not copied). Frozen spec:
docs/H13C_FULLTRAIN_PLAN.md.
"""

import json
import random
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import chz
from tinker_cookbook.rl.types import RLDatasetBuilder

from training.h13_env import SpreadsheetDataset
from training.reward import train_ids

OUT_DIR = RESEARCH.parent / "experiments" / "H13C-fulltrain-rlvr"


def full_train_task_list() -> list[str]:
    tids = sorted(train_ids())
    assert len(tids) == 280, f"train split must be 280 tasks, got {len(tids)}"
    rng = random.Random(42)
    rng.shuffle(tids)
    return tids


CONTEXT_WINDOW = 65536
GEN_BUDGET = 16384


def split_sampleable(tids, model_name, renderer_name):
    """Infra guard (not a spec change): a task whose routed observation plus
    the generation budget exceeds the model context can never yield an
    episode under ANY policy (the first attempt crashed the run mid-batch-3
    on a 342k-token observation). Deterministic, golden-free, documented."""
    from tinker_cookbook.model_info import get_recommended_renderer_name
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    from sb import load_dataset
    from training.h13_env import routed_messages

    name = renderer_name or get_recommended_renderer_name(model_name)
    from tinker_cookbook import renderers
    renderer = renderers.get_renderer(name, get_tokenizer(model_name))
    tasks = {t["id"]: t for t in load_dataset()}
    kept, excluded = [], []
    for tid in tids:
        system, user, _route = routed_messages(tasks[tid])
        convo = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        n = renderer.build_generation_prompt(convo).length
        if n + GEN_BUDGET > CONTEXT_WINDOW:
            excluded.append({"task_id": tid, "prompt_tokens": n})
        else:
            kept.append(tid)
    return kept, excluded


@chz.chz
class FullTrainDatasetBuilder(RLDatasetBuilder):
    model_name: str = "Qwen/Qwen3.8-27B"
    renderer_name: str = ""
    group_size: int = 4
    groups_per_batch: int = 20
    n_batches: int = 14
    smoke: bool = False

    async def __call__(self):
        tids = full_train_task_list()
        if self.smoke:
            tids = tids[: self.groups_per_batch * self.n_batches]
            excluded = []
        else:
            assert self.groups_per_batch * self.n_batches == len(tids), \
                "frozen budget = 280 group presentations (one nominal pass)"
            tids, excluded = split_sampleable(tids, self.model_name, self.renderer_name)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "frozen_tasks.json").write_text(json.dumps(
            {"task_ids": tids, "n_sampleable": len(tids),
             "excluded_unsampleable": excluded,
             "policy": ("uniform seed-42 shuffle; budget fixed at 280 presentations / "
                        "14 updates; unsampleable observations (prompt+16384 > 65536 ctx) "
                        "excluded loudly; presentation list wraps over sampleable tasks"),
             "group_size": self.group_size, "groups_per_batch": self.groups_per_batch,
             "n_batches": self.n_batches}, indent=1))
        return (SpreadsheetDataset(tids, self.groups_per_batch, self.group_size,
                                   self.n_batches, self.renderer_name, self.model_name), None)
