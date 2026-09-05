"""Locks the reward function to the official scorer. Run: uv run tests/test_reward_agreement.py

Test-side code: reads golden files deliberately (training/evaluation side).
The inference guard (test_golden_isolation.py) is unaffected — it scans
inference-side sources only.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))

from sb import load_dataset
from training.reward import REWARD_INVALID, REWARD_PASS, compute_reward


class RewardAgreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        train = set(json.loads((RESEARCH / "splits" / "train.json").read_text()))
        tasks = [t for t in load_dataset() if t["id"] in train and t["golden_xlsx"]]
        cls.task = tasks[0]
        cls.other = next(t for t in load_dataset() if t["id"] not in train)

    def test_golden_output_scores_full_pass_reward(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cand.xlsx"
            shutil.copy(self.task["golden_xlsx"], out)
            reward, item = compute_reward(self.task, out, td)
        self.assertEqual(item["status"], "graded")
        self.assertTrue(item["pass"])
        self.assertEqual(reward, REWARD_PASS)

    def test_init_output_scores_shaped_partial(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cand.xlsx"
            shutil.copy(self.task["init_xlsx"], out)
            reward, item = compute_reward(self.task, out, td)
        self.assertEqual(item["status"], "graded")
        if item["pass"]:  # degenerate task where init == golden; extremely unlikely
            self.assertEqual(reward, REWARD_PASS)
        else:
            expected = 0.2 * (item["correct"] / item["cells"] if item["cells"] else 0)
            self.assertAlmostEqual(reward, expected)
            self.assertLess(reward, 0.21)

    def test_missing_output_is_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            reward, item = compute_reward(self.task, Path(td) / "nope.xlsx", td)
        self.assertEqual(reward, REWARD_INVALID)

    def test_non_train_task_refused(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cand.xlsx"
            shutil.copy(self.other["init_xlsx"], out)
            with self.assertRaises(PermissionError):
                compute_reward(self.other, out, td)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
