"""One-shot generator of the fixed development splits. Run once, then never again.

Deterministic: task ids are sorted, shuffled with a fixed seed, and stratified by
instruction_type so each split keeps the 275/125 cell/sheet proportion:

    train      280  (193 cell + 87 sheet)   goldens may build training data later
    dev         60  ( 41 cell + 19 sheet)   harness/prompt/hyperparameter iteration
    local_test  60  ( 41 cell + 19 sheet)   held out; occasional generalisation checks only

The script refuses to run if any split file already exists. The split files are
version-controlled; regenerating or reshuffling them would invalidate every
experiment logged against them.
"""

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET = HERE.parent / "data" / "spreadsheetbench_verified_400" / "dataset.json"
SEED = 42
COUNTS = {"train": {"Cell-Level Manipulation": 193, "Sheet-Level Manipulation": 87},
          "dev": {"Cell-Level Manipulation": 41, "Sheet-Level Manipulation": 19},
          "local_test": {"Cell-Level Manipulation": 41, "Sheet-Level Manipulation": 19}}


def main():
    existing = [name for name in COUNTS if (HERE / f"{name}.json").exists()]
    if existing:
        sys.exit(f"refusing to run: split files already exist: {existing}. Never regenerate them.")

    tasks = json.loads(DATASET.read_text())
    by_type = {}
    for t in sorted(tasks, key=lambda t: str(t["id"])):
        by_type.setdefault(t["instruction_type"], []).append(str(t["id"]))

    rng = random.Random(SEED)
    for ids in by_type.values():
        rng.shuffle(ids)

    cursor = dict.fromkeys(by_type, 0)
    for name, want in COUNTS.items():
        split_ids = []
        for itype, n in want.items():
            split_ids.extend(by_type[itype][cursor[itype]:cursor[itype] + n])
            cursor[itype] += n
        (HERE / f"{name}.json").write_text(json.dumps(sorted(split_ids), indent=1) + "\n")
        print(f"{name}: {len(split_ids)} ids")

    assert all(cursor[t] == len(by_type[t]) for t in by_type), "not all tasks assigned"


if __name__ == "__main__":
    main()
