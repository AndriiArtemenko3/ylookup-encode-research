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
        assert self.groups_per_batch * self.n_batches == len(tids), \
            "frozen budget = exactly one coverage pass over all 280 train tasks"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "frozen_tasks.json").write_text(json.dumps(
            {"task_ids": tids, "n": len(tids), "policy": "uniform seed-42 shuffle, one pass",
             "group_size": self.group_size, "groups_per_batch": self.groups_per_batch,
             "n_batches": self.n_batches}))
        return (SpreadsheetDataset(tids, self.groups_per_batch, self.group_size,
                                   self.n_batches, self.renderer_name, self.model_name), None)
