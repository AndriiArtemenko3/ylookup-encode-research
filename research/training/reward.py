"""Verifiable reward for post-training. TRAINING SIDE ONLY.

This module is the single sanctioned bridge between golden data and learning:
the model never sees goldens; the verifier sees them only to score a candidate
output workbook AFTER it exists (model -> candidate -> verifier -> reward).

Reward shape (competition metric dominates, shaped tail keeps gradient):

    1.0                      every graded cell correct (task pass)
    0.2 * cell_accuracy      otherwise
    -0.1                     invalid / missing / unscorable output

Agreement with the official scorer is by construction: scoring goes through
evaluate.score_task itself (the judges' code path), and
tests/test_reward_agreement.py locks the mapping.

Integrity guard: rewards are computable ONLY for train-split tasks. dev and
local_test stay optimisation-free; asking for a reward there raises.
"""

import json
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))

from evaluate import score_task

_TRAIN_IDS: set[str] | None = None

REWARD_PASS = 1.0
REWARD_SHAPE = 0.2
REWARD_INVALID = -0.1


def train_ids() -> set[str]:
    global _TRAIN_IDS
    if _TRAIN_IDS is None:
        _TRAIN_IDS = set(json.loads((RESEARCH / "splits" / "train.json").read_text()))
    return _TRAIN_IDS


def compute_reward(task: dict, output_xlsx: str | Path, work_dir: str | Path,
                   *, recalc: bool = True) -> tuple[float, dict]:
    """Returns (reward, official_score_item). Train-split tasks only."""
    if str(task["id"]) not in train_ids():
        raise PermissionError(
            f"reward requested for task {task['id']} which is not in the train split; "
            f"dev/local_test are optimisation-free by policy")
    item = score_task(task, str(output_xlsx), recalc, str(work_dir))
    if item.get("status") != "graded":
        return REWARD_INVALID, item
    if item.get("pass"):
        return REWARD_PASS, item
    cells = item.get("cells") or 0
    cell_accuracy = (item.get("correct", 0) / cells) if cells else 0.0
    return REWARD_SHAPE * cell_accuracy, item
