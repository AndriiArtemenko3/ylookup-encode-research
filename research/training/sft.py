"""LoRA SFT on curated verified trajectories. Modeled on tinker_cookbook/recipes/sl_loop.py.

    uv run training/sft.py --dataset ../experiments/F1-rollouts/sft_dataset.jsonl \
        --log-path ../experiments/F1-sft --base-model Qwen/Qwen3.8-27B \
        [--max-steps 2]   # smoke first, per spec

Hyperparameters default to the workshop reference values (LoRA rank 32,
lr 5e-5) adjusted for our small dataset (batch 32, 2 epochs, linear decay).
Saves sampler weights at the end and records the tinker:// path in
manifest.json — that path is what --model-path takes at evaluation time.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

import os

import tinker
from common import load_env
from tinker_cookbook import model_info, renderers
from tinker_cookbook.supervised.common import compute_mean_nll
from tinker_cookbook.supervised.data import conversation_to_datum
from tinker_cookbook.tokenizer_utils import get_tokenizer

from experiments.manifest import build_manifest, write_manifest


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--log-path", required=True)
    p.add_argument("--base-model", default="Qwen/Qwen3.8-27B")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--max-length", type=int, default=32768)
    p.add_argument("--max-steps", type=int, help="smoke-test cap")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main():
    load_env()
    args = parse_args()
    log_path = Path(args.log_path)
    log_path.mkdir(parents=True, exist_ok=True)
    train_log = log_path / "train_log.jsonl"

    rows = [json.loads(l) for l in Path(args.dataset).read_text().splitlines() if l.strip()]
    rng = random.Random(args.seed)
    order = rows * args.epochs
    rng.shuffle(order)
    n_batches = len(order) // args.batch_size
    total_steps = min(n_batches, args.max_steps) if args.max_steps else n_batches
    print(f"examples={len(rows)} epochs={args.epochs} batch={args.batch_size} steps={total_steps}")

    tokenizer = get_tokenizer(args.base_model)
    renderer = renderers.get_renderer(model_info.get_recommended_renderer_name(args.base_model), tokenizer)
    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    client = service.create_lora_training_client(base_model=args.base_model, rank=args.rank)

    for step in range(total_steps):
        started = time.time()
        lr = args.lr * max(0.0, 1.0 - step / total_steps)
        adam = tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=1e-8)
        batch_rows = order[step * args.batch_size:(step + 1) * args.batch_size]
        batch = [conversation_to_datum(r["messages"], renderer, args.max_length,
                                       renderers.TrainOnWhat.ALL_ASSISTANT_MESSAGES)
                 for r in batch_rows]
        fwd = client.forward_backward(batch, loss_fn="cross_entropy")
        opt = client.optim_step(adam)
        fwd_result = fwd.result()
        opt.result()
        logprobs = [x["logprobs"] for x in fwd_result.loss_fn_outputs]
        weights = [d.loss_fn_inputs["weights"] for d in batch]
        nll = compute_mean_nll(logprobs, weights)
        record = {"step": step, "lr": lr, "mean_nll": float(nll),
                  "tokens": sum(d.model_input.length for d in batch),
                  "seconds": round(time.time() - started, 1)}
        with train_log.open("a") as f:
            f.write(json.dumps(record) + "\n")
        print(record, flush=True)

    future = client.save_weights_for_sampler(name="final")
    result = future.result()
    sampler_path = getattr(result, "path", None) or str(result)
    print("sampler weights:", sampler_path)

    manifest = build_manifest(
        log_path.name, model_id=args.base_model, checkpoint=sampler_path,
        harness_version="training:rsft-lora", prompt_version="champion-values-v0",
        dataset_split=f"sft:{Path(args.dataset).name}", task_ids=None,
        temperature=None, max_tokens=args.max_length, concurrency=None,
        retry_policy=f"lora r{args.rank} lr{args.lr} bs{args.batch_size} ep{args.epochs}",
        command=" ".join(sys.argv))
    write_manifest(log_path / "manifest.json", manifest)
    (log_path / "checkpoint.txt").write_text(sampler_path + "\n")


if __name__ == "__main__":
    main()
