"""Replay a past experiment's stored model responses through a new write path.

    uv run experiments/replay.py --source E002-maxtokens-24k-dev --id E003-faithful-write-dev

Zero model calls, zero tokens: for every task in the source experiment the
saved trace response is re-parsed and re-written with the CURRENT harness
writer (inference.write). This isolates write-path changes exactly — same
model outputs by construction, so any score delta is attributable to the
writer alone. Only valid for changes downstream of the model response.

Reads: source traces, dataset init workbooks. Never goldens.
"""

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
REPO_ROOT = RESEARCH.parent
EXPERIMENTS_ROOT = REPO_ROOT / "experiments"

sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="experiment id whose traces to replay")
    p.add_argument("--id", required=True, help="new experiment id")
    args = p.parse_args()

    src = EXPERIMENTS_ROOT / args.source
    dst = EXPERIMENTS_ROOT / args.id
    if dst.exists():
        sys.exit(f"refusing to overwrite existing experiment dir: {dst}")

    from experiments.manifest import build_manifest, write_manifest
    from inference.parse import parse_answer_lenient
    from inference.write import HARNESS_VERSION, write_output
    from sb import load_dataset

    src_manifest = json.loads((src / "manifest.json").read_text())
    tasks = {t["id"]: t for t in load_dataset()}
    src_predictions = [json.loads(line) for line in (src / "predictions.jsonl").read_text().splitlines() if line.strip()]

    (dst / "outputs").mkdir(parents=True)
    (dst / "traces").mkdir()
    started = time.time()
    log_lines = [f"replay of {args.source} through {HARNESS_VERSION} at {datetime.datetime.now(datetime.timezone.utc).isoformat()}"]

    n_ok = n_err = n_salvaged = 0
    with (dst / "predictions.jsonl").open("w", encoding="utf-8") as pred_file:
        for prediction in src_predictions:
            tid = prediction["id"]
            task = tasks[tid]
            trace = json.loads((src / "traces" / f"{tid}.jsonl").read_text())
            out = dst / "outputs" / f"{tid}.xlsx"
            try:
                # A stored response is worth parsing even when the source
                # harness recorded an error for it (its parser was stricter).
                if not trace["response"]:
                    raise ValueError(f"no response in source trace: {(trace['error'] or '?')[:120]}")
                answer, mode = parse_answer_lenient(trace["response"])
                write_output(task, answer, out)
                status = "ok" if mode == "strict" else "ok (salvaged)"
                n_ok += 1
                n_salvaged += mode == "salvaged"
            except Exception as e:
                shutil.copy(task["init_xlsx"], out)
                status = f"error: {e}"[:200]
                n_err += 1
            shutil.copy(src / "traces" / f"{tid}.jsonl", dst / "traces" / f"{tid}.jsonl")
            pred_file.write(json.dumps({"id": tid, "output": f"outputs/{tid}.xlsx", "status": status}) + "\n")
            log_lines.append(f"{tid:<8} {status}")

    manifest = build_manifest(
        args.id,
        model_id=src_manifest.get("model_id"),
        checkpoint=src_manifest.get("checkpoint"),
        harness_version=f"{HARNESS_VERSION} (replay of {args.source})",
        prompt_version=src_manifest.get("prompt_version"),
        dataset_split=src_manifest.get("dataset_split"),
        task_ids=src_manifest.get("task_ids"),
        temperature=src_manifest.get("temperature"),
        max_tokens=src_manifest.get("max_tokens"),
        concurrency=None,
        retry_policy="none",
        command=f"replay --source {args.source}",
    )
    manifest["wall_clock_seconds"] = round(time.time() - started, 1)
    manifest["replay_of"] = args.source
    write_manifest(dst / "manifest.json", manifest)
    log_lines.append(f"rewritten ok={n_ok} (salvaged={n_salvaged}) error={n_err}")
    (dst / "run.log").write_text("\n".join(log_lines) + "\n")
    (dst / "notes.md").write_text(f"# {args.id}\n\nReplay of {args.source} through {HARNESS_VERSION}.\n")

    subprocess.run([sys.executable, str(RESEARCH / "evaluate.py"),
                    "--predictions", str(dst / "predictions.jsonl"), "--quiet",
                    "--out", str(dst / "results.json")], cwd=RESEARCH, check=False)
    if (dst / "results.json").exists():
        print(json.dumps(json.loads((dst / "results.json").read_text())["summary"], indent=2))


if __name__ == "__main__":
    main()
