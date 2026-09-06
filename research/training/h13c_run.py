"""H13C launcher: cookbook rl.train.main, full-280-train coverage pass.

    uv run training/h13c_run.py [--smoke]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from common import load_env

load_env()
os.environ.setdefault("TINKER_PROJECT_ID", os.environ.get("TINKER_PROJECT_ID", ""))

from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.rl import train as rl_train

from training.h13c_env import FullTrainDatasetBuilder


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--log-path", default=str(RESEARCH.parent / "experiments" / "H13C-fulltrain-rlvr"))
    args = p.parse_args()

    model = "Qwen/Qwen3.8-27B"
    renderer = get_recommended_renderer_name(model)
    if args.smoke:
        builder = FullTrainDatasetBuilder(
            model_name=model, renderer_name=renderer,
            group_size=2, groups_per_batch=2, n_batches=1, smoke=True)
    else:
        builder = FullTrainDatasetBuilder(model_name=model, renderer_name=renderer)
    cfg = rl_train.Config(
        learning_rate=1e-5,
        dataset_builder=builder,
        model_name=model,
        recipe_name="recipe_spreadsheet_rlvr_h13c",
        max_tokens=2048 if args.smoke else 16384,
        log_path=args.log_path + ("-smoke" if args.smoke else ""),
        renderer_name=renderer,
        save_every=4,
        eval_every=0,
        lora_rank=32,
    )
    asyncio.run(rl_train.main(cfg))


if __name__ == "__main__":
    main()
