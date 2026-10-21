"""CPU-only validation for the private G2-01 plan and truth helper."""

import json
import stat
import tempfile
import unittest
from pathlib import Path

from tools.g2_01_inject import (
    episode_for,
    load_plan,
    sleep_for_episode,
    validate_capture_bounds,
    write_rank_truth,
)


def valid_document():
    return {
        "schema": "g2-01-plan-v1",
        "nonce": "private_nonce-01",
        "episodes": [
            {"step": step, "rank": rank, "delay_s": 0.02}
            for step, rank in zip(range(0, 24, 3), (0, 0, 1, 1, 2, 2, 3, 3))
        ],
    }


class G201InjectPlanTests(unittest.TestCase):
    def _load_document(self, document, *, steps=24, warmup=5, world_size=4):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return load_plan(path, steps=steps, warmup=warmup, world_size=world_size)

    def test_accepts_exact_bounded_plan_and_selects_only_matching_rank_step(self):
        plan = self._load_document(valid_document())
        self.assertEqual(plan["schema"], "g2-01-plan-v1")
        self.assertEqual(plan["nonce"], "private_nonce-01")
        self.assertEqual(episode_for(plan, step=6, rank=1), {"step": 6, "rank": 1, "delay_s": 0.02})
        self.assertIsNone(episode_for(plan, step=6, rank=2))
        self.assertIsNone(episode_for(None, step=6, rank=1))

    def test_rejects_wrong_world_warmup_and_out_of_range_step(self):
        with self.assertRaisesRegex(ValueError, "four ranks"):
            self._load_document(valid_document(), world_size=2)
        with self.assertRaisesRegex(ValueError, "five warmup"):
            self._load_document(valid_document(), warmup=4)
        with self.assertRaisesRegex(ValueError, "outside"):
            self._load_document(valid_document(), steps=21)

    def test_healthy_truth_capture_uses_the_same_four_rank_and_warmup_bounds(self):
        validate_capture_bounds(steps=40, warmup=5, world_size=4)
        with self.assertRaisesRegex(ValueError, "four ranks"):
            validate_capture_bounds(steps=40, warmup=5, world_size=2)
        with self.assertRaisesRegex(ValueError, "five warmup"):
            validate_capture_bounds(steps=40, warmup=3, world_size=4)

    def test_rejects_bad_shape_spacing_rank_counts_and_delay(self):
        cases = []
        malformed = valid_document()
        malformed["unexpected"] = True
        cases.append((malformed, "exactly schema"))

        malformed = valid_document()
        malformed["episodes"][1]["step"] = malformed["episodes"][0]["step"]
        cases.append((malformed, "distinct"))

        malformed = valid_document()
        malformed["episodes"][1]["step"] = malformed["episodes"][0]["step"] + 1
        cases.append((malformed, "at least one measured step"))

        malformed = valid_document()
        malformed["episodes"][0]["rank"] = 3
        cases.append((malformed, "exactly two episodes"))

        malformed = valid_document()
        malformed["episodes"][0]["delay_s"] = 0.01
        cases.append((malformed, "0.020 seconds"))

        for document, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self._load_document(document)

    def test_sleep_records_actual_monotonic_duration(self):
        truth = sleep_for_episode({"delay_s": 0.02})
        self.assertGreaterEqual(truth["sleep_end_monotonic_ns"], truth["sleep_start_monotonic_ns"])
        self.assertGreaterEqual(truth["actual_delay_s"], 0.02)
        self.assertEqual(truth["scheduled_delay_s"], 0.02)
        self.assertIsNone(sleep_for_episode(None))

    def test_truth_file_is_private_atomic_and_create_exclusive(self):
        boundaries = [{"step": 0, "start_monotonic_ns": 10, "end_monotonic_ns": 20, "injection": None}]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "truth"
            plan = self._load_document(valid_document())
            path = write_rank_truth(output, rank=0, steps=24, warmup=5,
                                    plan=plan, step_boundaries=boundaries)
            self.assertEqual(path, output / "rank-0.json")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["schema"], "g2-01-truth-v1")
            self.assertEqual(record["plan_nonce"], "private_nonce-01")
            self.assertEqual(record["step_boundaries"], boundaries)
            with self.assertRaises(FileExistsError):
                write_rank_truth(output, rank=0, steps=24, warmup=5,
                                 plan=None, step_boundaries=[])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["plan_nonce"], "private_nonce-01")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "plan.json"
            path.write_text('{"schema":"g2-01-plan-v1","schema":"g2-01-plan-v1"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate key"):
                load_plan(path, steps=24, warmup=5, world_size=4)


if __name__ == "__main__":
    unittest.main()
