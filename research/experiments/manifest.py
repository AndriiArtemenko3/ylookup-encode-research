"""Manifest capture for reproducible experiments. Stdlib only."""

import datetime
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def _soffice_version() -> str:
    sys.path.insert(0, str(REPO_ROOT / "research"))
    try:
        from sb import soffice_path
        exe = soffice_path()
        if not exe:
            return "not found"
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or exe
    except Exception as e:
        return f"unknown ({type(e).__name__})"


def build_manifest(
    experiment_id: str,
    *,
    model_id: str | None = None,
    checkpoint: str | None = None,
    harness_version: str = "baseline-untouched",
    prompt_version: str = "baseline-v0",
    dataset_split: str | None = None,
    task_ids: list[str] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    concurrency: int | None = None,
    retry_policy: str = "none",
    command: str | None = None,
) -> dict:
    return {
        "experiment_id": experiment_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty_worktree": bool(_git("status", "--porcelain")),
        "model_id": model_id,
        "checkpoint": checkpoint,
        "harness_version": harness_version,
        "prompt_version": prompt_version,
        "dataset_split": dataset_split,
        "task_ids": task_ids,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "concurrency": concurrency,
        "retry_policy": retry_policy,
        "command": command,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": platform.node(),
            "soffice": _soffice_version(),
            "cwd": os.getcwd(),
        },
        "wall_clock_seconds": None,  # filled in by the runner on completion
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n")
