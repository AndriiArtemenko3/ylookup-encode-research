"""F1v2 corrected RSFT: LoRA training on EXACT sampled token trajectories.

    uv run training/sft2.py --dataset .../sft_dataset_v2.jsonl \
        --log-path ../experiments/F1v2-sft-lr1e5 --lr 1e-5 [--max-steps 2]

Faithfulness: each datum is ModelInput.from_ints(prompt_ids + completion_ids)
with loss weights 0 on the prompt and 1 on the completion — the training
labels ARE the sampled tokens that produced the verifier-approved workbook.
No re-rendering, no template reconstruction, reasoning fully preserved.

Exposure accounting is in ASSISTANT TOKENS. Sampler checkpoints are saved at
~25% / 50% / 100% cumulative assistant-token exposure (named ckpt-25pct /
ckpt-50pct / final) for the successive-halving canary protocol. One data pass
(100% exposure) is the default budget; epochs are not the unit.
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
import torch
from common import load_env
from tinker_cookbook.supervised.common import compute_mean_nll, datum_from_model_input_weights

from experiments.manifest import build_manifest, write_manifest


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--log-path", required=True)
    p.add_argument("--base-model", default="Qwen/Qwen3.8-27B")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--lr", type=float, required=True)
    p.add_argument("--batch-size", type=int, default=8, help="sequences per step (long trajectories)")
    p.add_argument("--passes", type=float, default=1.0, help="dataset passes (1.0 = 100% token exposure)")
    p.add_argument("--max-length", type=int, default=32768)
    p.add_argument("--max-steps", type=int, help="smoke cap")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def to_datum(example, max_length):
    prompt, completion = example["prompt_token_ids"], example["completion_token_ids"]
    ids = prompt + completion
    weights = torch.tensor([0.0] * len(prompt) + [1.0] * len(completion))
    return datum_from_model_input_weights(tinker.ModelInput.from_ints(ids), weights,
                                          max_length=max_length, reduction="mean")


def main():
    load_env()
    args = parse_args()
    log_path = Path(args.log_path)
    log_path.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in Path(args.dataset).read_text().splitlines() if l.strip()]
    rng = random.Random(args.seed)
    order = rows * int(args.passes) + rng.sample(rows, int(len(rows) * (args.passes % 1)))
    rng.shuffle(order)
    n_batches = len(order) // args.batch_size
    total_steps = min(n_batches, args.max_steps) if args.max_steps else n_batches
    dataset_tokens = sum(len(r["completion_token_ids"]) for r in rows)
    print(f"examples={len(rows)} dataset assistant tokens={dataset_tokens:,} "
          f"passes={args.passes} steps={total_steps} bs={args.batch_size}")

    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    client = service.create_lora_training_client(base_model=args.base_model, rank=args.rank)

    exposure = 0
    marks = {0.25: "ckpt-25pct", 0.50: "ckpt-50pct"}
    saved = set()
    target_exposure = dataset_tokens * args.passes
    for step in range(total_steps):
        started = time.time()
        lr = args.lr * max(0.0, 1.0 - step / total_steps)
        adam = tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=1e-8)
        batch_rows = order[step * args.batch_size:(step + 1) * args.batch_size]
        batch = [to_datum(r, args.max_length) for r in batch_rows]
        fwd = client.forward_backward(batch, loss_fn="cross_entropy")
        opt = client.optim_step(adam)
        fwd_result = fwd.result(); opt.result()
        exposure += sum(len(r["completion_token_ids"]) for r in batch_rows)
        logprobs = [x["logprobs"] for x in fwd_result.loss_fn_outputs]
        weights = [d.loss_fn_inputs["weights"] for d in batch]
        nll = float(compute_mean_nll(logprobs, weights))
        rec = {"step": step, "lr": lr, "mean_nll": round(nll, 4),
               "assistant_tokens_seen": exposure,
               "exposure_frac": round(exposure / target_exposure, 3),
               "seconds": round(time.time() - started, 1)}
        with (log_path / "train_log.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(rec, flush=True)
        for frac, name in marks.items():
            if name not in saved and exposure >= target_exposure * frac:
                path = getattr(client.save_weights_for_sampler(name=name).result(), "path", "?")
                (log_path / f"{name}.txt").write_text(str(path) + "\n")
                saved.add(name)
                print(f"saved {name}: {path}", flush=True)

    final = getattr(client.save_weights_for_sampler(name="final").result(), "path", "?")
    (log_path / "checkpoint.txt").write_text(str(final) + "\n")
    print("final:", final)
    manifest = build_manifest(
        log_path.name, model_id=args.base_model, checkpoint=str(final),
        harness_version="training:rsft-v2-raw-tokens", prompt_version="champion-values-v0",
        dataset_split=f"sftv2:{Path(args.dataset).name}", task_ids=None,
        temperature=None, max_tokens=args.max_length, concurrency=None,
        retry_policy=f"lora r{args.rank} lr{args.lr} bs{args.batch_size} passes{args.passes} "
                     f"assistant_tokens={exposure}",
        command=" ".join(sys.argv))
    manifest["assistant_token_exposure"] = exposure
    write_manifest(log_path / "manifest.json", manifest)


if __name__ == "__main__":
    main()
