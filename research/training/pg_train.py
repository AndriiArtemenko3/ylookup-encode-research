"""H12: on-policy policy-gradient (REINFORCE) over stored trajectories.

    uv run training/pg_train.py --reward R0|R1|R2 --log-path ../experiments/H12-R0 [--max-steps 1]

Implements docs/H12_REWARD_ABLATION_PLAN.md exactly: frozen band, frozen
rewards, group-relative clipped advantages as signed per-token weights on the
EXACT sampled completion tokens (prompt weight 0, reduction="none"). All arms
share every constant except the reward function.
"""

import argparse
import json
import random
import statistics
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

ROLLOUTS = RESEARCH.parent / "experiments" / "F1v2-rollouts-reasoning-preserved" / "rollouts"


def bucket(c):
    if not c["valid"]:
        return "INVALID"
    if c["pass"]:
        return "EXACT"
    if c["wrong"] is not None and c["wrong"] <= 5 and c["acc"] >= 0.90:
        return "NEAR_EXACT"
    if c["acc"] >= 0.30:
        return "PARTIAL"
    return "FAIL"


def make_reward(name):
    if name == "R0":
        return lambda c: 1.0 if c["pass"] else (0.2 * c["acc"] if c["valid"] else -0.1)
    if name == "R1":
        vals = {"EXACT": 1.0, "NEAR_EXACT": 0.5, "PARTIAL": 0.2, "FAIL": 0.02, "INVALID": -0.1}
        return lambda c: vals[bucket(c)]
    if name == "R2":
        def r2(c):
            b = bucket(c)
            return {"EXACT": 1.0, "NEAR_EXACT": 0.45 + 0.10 * c["acc"],
                    "PARTIAL": 0.15 + 0.10 * c["acc"], "FAIL": 0.02 * c["acc"],
                    "INVALID": -0.1}[b]
        return r2
    raise SystemExit(f"unknown reward {name}")


def load_band():
    """Frozen band per plan: mixed pass/fail groups, or all-fail with acc spread >= 0.10."""
    band = []
    for d in sorted(ROLLOUTS.iterdir()):
        pt = d / "prompt_tokens.json"
        if not pt.exists():
            continue
        prompt_ids = json.loads(pt.read_text())["prompt_token_ids"]
        cands = []
        for f in sorted(d.glob("[0-9]*.json")):
            r = json.loads(f.read_text())
            s = r.get("score") or {}
            cells = s.get("cells") or 0
            c = {"pass": bool(s.get("pass")), "valid": s.get("status") == "graded",
                 "acc": (s.get("correct") or 0) / cells if cells else 0.0,
                 "wrong": (cells - (s.get("correct") or 0)) if s.get("status") == "graded" else None,
                 "tokens": r.get("completion_token_ids")}
            if c["tokens"]:
                cands.append(c)
        if len(cands) < 2:
            continue
        passes = [c["pass"] for c in cands]
        accs = [c["acc"] for c in cands]
        if (any(passes) and not all(passes)) or (not any(passes) and max(accs) - min(accs) >= 0.10):
            band.append({"task": d.name, "prompt": prompt_ids, "cands": cands})
    return band


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reward", required=True, choices=["R0", "R1", "R2"])
    p.add_argument("--log-path", required=True)
    p.add_argument("--lr", type=float, default=1e-5)
    p.add_argument("--groups-per-step", type=int, default=4)
    p.add_argument("--max-steps", type=int)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    load_env()
    log_path = Path(args.log_path)
    log_path.mkdir(parents=True, exist_ok=True)

    reward_fn = make_reward(args.reward)
    band = load_band()
    rng = random.Random(args.seed)
    rng.shuffle(band)
    total_tokens = sum(len(c["tokens"]) for g in band for c in g["cands"])
    n_steps = len(band) // args.groups_per_step
    total_steps = min(n_steps, args.max_steps) if args.max_steps else n_steps
    print(f"[{args.reward}] band groups={len(band)} completion tokens={total_tokens:,} steps={total_steps}")

    service = tinker.ServiceClient(project_id=os.environ.get("TINKER_PROJECT_ID") or None)
    client = service.create_lora_training_client(base_model="Qwen/Qwen3.8-27B", rank=32)

    exposure, saved = 0, set()
    marks = {0.25: "ckpt-25pct", 0.50: "ckpt-50pct"}
    for step in range(total_steps):
        started = time.time()
        lr = args.lr * max(0.0, 1.0 - step / total_steps)
        groups = band[step * args.groups_per_step:(step + 1) * args.groups_per_step]
        batch = []
        for g in groups:
            rs = [reward_fn(c) for c in g["cands"]]
            mu, sd = statistics.mean(rs), statistics.pstdev(rs)
            for c, r in zip(g["cands"], rs):
                adv = max(-2.0, min(2.0, (r - mu) / (sd + 1e-4)))
                if abs(adv) < 1e-6:
                    continue
                w = adv / len(c["tokens"])
                ids = g["prompt"] + c["tokens"]
                weights = torch.tensor([0.0] * len(g["prompt"]) + [w] * len(c["tokens"]))
                batch.append(datum_from_model_input_weights(
                    tinker.ModelInput.from_ints(ids), weights, max_length=32768, reduction="none"))
                exposure += len(c["tokens"])
        if not batch:
            continue
        fb = client.forward_backward(batch, loss_fn="cross_entropy")
        op = client.optim_step(tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=1e-8))
        res = fb.result(); op.result()
        nll = float(compute_mean_nll([x["logprobs"] for x in res.loss_fn_outputs],
                                     [d.loss_fn_inputs["weights"] for d in batch]))
        rec = {"step": step, "lr": lr, "signed_weighted_nll": round(nll, 4),
               "sequences": len(batch), "exposure_tokens": exposure,
               "seconds": round(time.time() - started, 1)}
        with (log_path / "train_log.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{args.reward}]", rec, flush=True)
        for frac, name in marks.items():
            if name not in saved and step + 1 >= total_steps * frac:
                path = getattr(client.save_weights_for_sampler(name=name).result(), "path", "?")
                (log_path / f"{name}.txt").write_text(str(path) + "\n")
                saved.add(name)

    final = getattr(client.save_weights_for_sampler(name="final").result(), "path", "?")
    (log_path / "checkpoint.txt").write_text(str(final) + "\n")
    print(f"[{args.reward}] final:", final)
    manifest = build_manifest(log_path.name, model_id="Qwen/Qwen3.8-27B", checkpoint=str(final),
                              harness_version=f"training:pg-{args.reward}", prompt_version="champion-values-v0",
                              dataset_split="H12 frozen band", task_ids=None, temperature=None,
                              max_tokens=32768, concurrency=None,
                              retry_policy=f"REINFORCE {args.reward} lr{args.lr} clip2 gps{args.groups_per_step}",
                              command=" ".join(sys.argv))
    manifest["band_groups"] = len(band)
    manifest["exposure_tokens"] = exposure
    write_manifest(log_path / "manifest.json", manifest)


if __name__ == "__main__":
    main()
