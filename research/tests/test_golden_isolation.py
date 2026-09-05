"""Guards for the benchmark contract. Run with: uv run tests/test_golden_isolation.py

1. Golden isolation: inference-side code (baseline/, inference/, tools/,
   telemetry.py) must never reference golden workbooks. Goldens are readable
   only by evaluation (evaluate.py, sb.py) and training-data construction
   (training/).
2. Split integrity: the frozen split files in splits/ must keep their exact
   ids (counts, disjointness, stratification, checksum). They are never
   regenerated.
"""

import ast
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]

INFERENCE_SOURCES = ["baseline", "inference", "tools", "telemetry.py"]
GOLDEN_PATTERN = re.compile(r"golden", re.IGNORECASE)

# sha256 of the sorted id list of each frozen split. If this test fails the
# split files were modified: restore them from git, do NOT update the hashes.
SPLIT_CHECKSUMS = {
    "train": ("111540cc2d18a6de0cd54e4d14330496776a8ece72b5a695dc7b104ac9888669", 280),
    "dev": ("3d79d2c75ec153ec4eaad6d555c3073171f530ad332d7fcc09a6b880e982c635", 60),
    "local_test": ("93d6ea420145ab8b60697140ecc12433e69b4fa31e7de9a1beec264cc05495c8", 60),
}


def iter_inference_files():
    for entry in INFERENCE_SOURCES:
        path = RESEARCH / entry
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def docstring_lines(source: str) -> set[int]:
    """Line numbers occupied by docstrings; documentation may name the rule it enforces."""
    lines: set[int] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            lines.update(range(body[0].lineno, (body[0].end_lineno or body[0].lineno) + 1))
    return lines


class GoldenIsolation(unittest.TestCase):
    def test_inference_code_never_mentions_golden(self):
        offenders = []
        for path in iter_inference_files():
            source = path.read_text()
            skip = docstring_lines(source)
            for lineno, line in enumerate(source.splitlines(), 1):
                if lineno in skip or line.lstrip().startswith("#") or "guard-ok" in line:
                    continue
                if GOLDEN_PATTERN.search(line):
                    offenders.append(f"{path.relative_to(RESEARCH)}:{lineno}: {line.strip()}")
        self.assertEqual(offenders, [],
                         "inference-side code must never touch golden data:\n" + "\n".join(offenders))


class SplitIntegrity(unittest.TestCase):
    def load(self, name):
        return json.loads((RESEARCH / "splits" / f"{name}.json").read_text())

    def test_counts_and_checksums(self):
        for name, (sha, count) in SPLIT_CHECKSUMS.items():
            ids = self.load(name)
            self.assertEqual(len(ids), count, f"{name} count changed")
            digest = hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()
            self.assertEqual(digest, sha,
                             f"{name}.json content changed — restore it from git, never regenerate")

    def test_disjoint_and_complete(self):
        splits = {name: self.load(name) for name in SPLIT_CHECKSUMS}
        combined = sum(splits.values(), [])
        self.assertEqual(len(combined), 400)
        self.assertEqual(len(set(combined)), 400, "splits overlap")


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
