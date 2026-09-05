"""Run a prediction command as a tracked experiment. Stdlib only.

    uv run experiments/runner.py --id E001-example --split dev \
        --model Qwen/Qwen3-8B --harness baseline-untouched \
        -- uv run baseline/tinker_predict.py --base-model Qwen/Qwen3-8B \
           --out-dir {out_dir} --ids {ids}

Everything after `--` is the prediction command. `{out_dir}` is replaced with
the experiment directory, `{ids}` with the comma-joined split ids. The runner:

1. refuses to reuse an existing experiments/<id>/ directory (never overwrite);
2. captures manifest.json (git commit, split, params, command, runtime);
3. tees the command's stdout/stderr into run.log;
4. scores the run with the official evaluate.py, unchanged, into results.json;
5. appends start/end events to events.jsonl.

The prediction command must write predictions.jsonl, outputs/, traces/ and
run.log into {out_dir} (the baselines already do).
"""

import argparse
import datetime
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
REPO_ROOT = RESEARCH.parent
EXPERIMENTS_ROOT = REPO_ROOT / "experiments"


def load_split(name: str) -> list[str] | None:
    if name == "all":
        return None
    path = RESEARCH / "splits" / f"{name}.json"
    if not path.exists():
        sys.exit(f"unknown split {name!r}: {path} does not exist")
    return json.loads(path.read_text())


def append_event(path: Path, event: str, **fields) -> None:
    record = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="experiment id, e.g. E001-formulas")
    p.add_argument("--split", default="all", help="train | dev | local_test | all")
    p.add_argument("--model", help="model id for the manifest")
    p.add_argument("--checkpoint", help="tinker:// checkpoint for the manifest")
    p.add_argument("--harness", default="baseline-untouched")
    p.add_argument("--prompt-version", default="baseline-v0")
    p.add_argument("--temperature", type=float)
    p.add_argument("--max-tokens", type=int)
    p.add_argument("--concurrency", type=int)
    p.add_argument("--retry-policy", default="none")
    p.add_argument("--no-eval", action="store_true", help="skip the evaluate.py step")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="prediction command after --, with {out_dir} and {ids} placeholders")
    args = p.parse_args()

    exp_dir = EXPERIMENTS_ROOT / args.id
    if exp_dir.exists():
        sys.exit(f"refusing to overwrite existing experiment dir: {exp_dir}\n"
                 f"Pick a new id; experiment directories are append-only.")
    command = [c for c in args.command if c != "--"]
    if not command:
        sys.exit("no prediction command given (put it after --)")

    ids = load_split(args.split)
    exp_dir.mkdir(parents=True)
    (exp_dir / "notes.md").write_text(f"# {args.id}\n\n- Hypothesis:\n- Primary change:\n- Result:\n")
    events = exp_dir / "events.jsonl"

    command = [c.replace("{out_dir}", str(exp_dir)).replace("{ids}", ",".join(ids or [])) for c in command]

    sys.path.insert(0, str(RESEARCH))
    from experiments.manifest import build_manifest, write_manifest

    manifest = build_manifest(
        args.id, model_id=args.model, checkpoint=args.checkpoint,
        harness_version=args.harness, prompt_version=args.prompt_version,
        dataset_split=args.split, task_ids=ids, temperature=args.temperature,
        max_tokens=args.max_tokens, concurrency=args.concurrency,
        retry_policy=args.retry_policy, command=shlex.join(command),
    )
    write_manifest(exp_dir / "manifest.json", manifest)
    if manifest["dirty_worktree"]:
        print("WARNING: dirty worktree — results will not be exactly attributable to a commit", file=sys.stderr)

    append_event(events, "experiment.start", experiment_id=args.id, split=args.split,
                 n_tasks=len(ids) if ids else "all", command=shlex.join(command))
    started = time.time()
    run_log = exp_dir / "run.log"
    with run_log.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=RESEARCH, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        returncode = proc.wait()
    elapsed = round(time.time() - started, 1)
    append_event(events, "experiment.predict_done", returncode=returncode, wall_clock_seconds=elapsed)

    manifest["wall_clock_seconds"] = elapsed
    write_manifest(exp_dir / "manifest.json", manifest)

    predictions = exp_dir / "predictions.jsonl"
    if not args.no_eval and predictions.exists():
        eval_cmd = [sys.executable, str(RESEARCH / "evaluate.py"),
                    "--predictions", str(predictions), "--quiet",
                    "--out", str(exp_dir / "results.json")]
        if args.split == "all":
            eval_cmd.append("--all")
        subprocess.run(eval_cmd, cwd=RESEARCH, check=False)
        if (exp_dir / "results.json").exists():
            summary = json.loads((exp_dir / "results.json").read_text())["summary"]
            append_event(events, "evaluation.done", **summary)
            print(json.dumps(summary, indent=2))
    elif not predictions.exists():
        append_event(events, "evaluation.skipped", reason="no predictions.jsonl")
        print("no predictions.jsonl produced; evaluation skipped", file=sys.stderr)

    append_event(events, "experiment.end", returncode=returncode)
    sys.exit(returncode)


if __name__ == "__main__":
    main()
