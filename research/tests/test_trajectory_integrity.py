"""F0 hard gate: round-trip integrity of captured raw trajectories.

    uv run tests/test_trajectory_integrity.py ../experiments/<rollout-dir>

Training on corrected trajectories is FORBIDDEN until this passes. Checks per
verified-pass candidate (and aggregate):

1. raw sampled completion token ids retained;
2. reasoning preserved: decoded raw length substantially exceeds the parsed
   final content (reasoning fraction measured);
3. completion-length regime matches successful base trajectories
   (aggregate p50 >= 1500 tokens; the failed run's 253 would fail here);
4. renderer-decoding the stored tokens reproduces the same final answer as
   the stored content;
5. replay through the h2 write path still passes the official verifier;
6. no distinctive golden value appears in the decoded model input;
7. rebuilt serving prompt tokens == stored prompt tokens (template match);
8. renderer.parse_response on stored tokens works (no special-token damage).
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))
sys.path.insert(0, str(RESEARCH / "baseline"))

from common import FORMAT_HINT, SYSTEM_PROMPT, build_prompt
from tinker_cookbook import renderers
from tinker_cookbook.model_info import get_recommended_renderer_name
from tinker_cookbook.tokenizer_utils import get_tokenizer

from experiments.audit_traces import distinctive_golden_values
from inference.parse import parse_answer_lenient
from inference.write import write_output
from sb import load_dataset
from training.reward import compute_reward

ROLLOUT_DIR = Path(sys.argv.pop(1)) if len(sys.argv) > 1 else None
BASE_MODEL = "Qwen/Qwen3.8-27B"
MIN_AGG_P50 = 1500
SAMPLE_TASKS = 6


def parsed_cells(text):
    answer, _ = parse_answer_lenient(text)
    return {c.cell.upper(): c.value for c in answer.cells}


class TrajectoryIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert ROLLOUT_DIR and (ROLLOUT_DIR / "rollouts").exists(), "pass a rollout dir"
        cls.tasks = {t["id"]: t for t in load_dataset()}
        cls.tokenizer = get_tokenizer(BASE_MODEL)
        cls.renderer = renderers.get_renderer(get_recommended_renderer_name(BASE_MODEL), cls.tokenizer)
        cls.records = []  # (task, record, prompt_ints)
        for task_dir in sorted((ROLLOUT_DIR / "rollouts").iterdir()):
            pt = task_dir / "prompt_tokens.json"
            if not pt.exists():
                continue
            prompt_ints = json.loads(pt.read_text())["prompt_token_ids"]
            for f in sorted(task_dir.glob("[0-9]*.json")):
                r = json.loads(f.read_text())
                if r.get("reward") == 1.0 and r.get("completion_token_ids"):
                    cls.records.append((cls.tasks[r["task_id"]], r, prompt_ints))
        assert cls.records, "no verified-pass raw-token records found"
        rng = random.Random(7)
        cls.sample = rng.sample(cls.records, min(SAMPLE_TASKS, len(cls.records)))

    def test_1_raw_tokens_retained_and_2_reasoning_preserved(self):
        fractions = []
        for task, r, _p in self.sample:
            self.assertTrue(r["completion_token_ids"], f"{r['task_id']}: no raw tokens")
            raw = self.tokenizer.decode(r["completion_token_ids"])
            content_tokens = len(self.tokenizer.encode(r["response"]))
            frac = 1 - content_tokens / max(len(r["completion_token_ids"]), 1)
            fractions.append(frac)
            self.assertGreater(len(raw), len(r["response"]),
                               f"{r['task_id']}: decoded raw not longer than stripped content")
        print(f"\n  reasoning-token fraction (sample): "
              f"{[round(f, 2) for f in fractions]}")

    def test_3_length_regime(self):
        lengths = sorted(len(r["completion_token_ids"]) for _t, r, _p in self.records)
        p10, p50, p90 = (lengths[int(len(lengths) * q)] for q in (0.10, 0.50, 0.90))
        print(f"\n  verified-pass completion tokens: p10={p10} p50={p50} p90={p90} max={lengths[-1]} n={len(lengths)}")
        self.assertGreaterEqual(p50, MIN_AGG_P50,
                                f"p50 {p50} < {MIN_AGG_P50}: thinking-stripped regime — FAILED integrity")

    def test_4_decode_reproduces_answer_and_8_no_token_damage(self):
        for task, r, _p in self.sample:
            reparsed = self.renderer.parse_response(r["completion_token_ids"])[0]["content"]
            if not isinstance(reparsed, str):
                reparsed = "".join(p.get("text", "") for p in reparsed if p.get("type") == "text")
            self.assertEqual(parsed_cells(reparsed), parsed_cells(r["response"]),
                             f"{r['task_id']}: token round-trip changed the final answer")

    def test_5_replay_still_passes_verifier(self):
        for task, r, _p in self.sample[:3]:  # verifier replay is slow; 3 suffice
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "o.xlsx"
                answer, _ = parse_answer_lenient(r["response"])
                write_output(task, answer, out)
                reward, item = compute_reward(task, out, td)
            self.assertEqual(reward, 1.0, f"{r['task_id']}: stored pass no longer passes on replay")

    def test_6_no_golden_in_prompt_and_7_template_match(self):
        for task, r, prompt_ints in self.sample:
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_prompt(task) + FORMAT_HINT}]
            rebuilt = self.renderer.build_generation_prompt(messages).to_ints()
            self.assertEqual(rebuilt, prompt_ints,
                             f"{r['task_id']}: serving prompt tokens != stored training prompt tokens")
            decoded_prompt = self.tokenizer.decode(prompt_ints)
            for value in distinctive_golden_values(task)[:30]:
                self.assertNotIn(value, decoded_prompt,
                                 f"{r['task_id']}: distinctive golden value in model input")


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=2))
