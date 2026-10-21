"""Synthetic CPU-only checks for G2-01 blind reveal/scoring logic."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.g2_01_score import freeze, main, score, sha


EPISODES = [(step, rank) for step, rank in zip((2, 6, 10, 14, 18, 22, 26, 30), (0, 0, 1, 1, 2, 2, 3, 3))]
HEALTHY_STEPS = [0, 4, 8, 12, 16, 20, 24, 28]


def make_inputs(*, injection_specs=None, healthy_specs=None, ineffective=False, unmapped=None):
    """Build an entirely synthetic, structurally complete scoring case."""
    plan = {
        "schema": "g2-01-plan-v1",
        "nonce": "cpu-score-fixture",
        "episodes": [{"step": step, "rank": rank, "delay_s": 0.02} for step, rank in EPISODES],
    }
    truths = {}
    for rank in range(4):
        boundaries = []
        for step in range(40):
            start = 10_000_000_000 + rank * 100_000_000_000 + step * 100_000_000
            end = start + 50_000_000
            injection = None
            if (step, rank) in EPISODES:
                sleep_start = start + 5_000_000
                sleep_ms = 10_000_000 if ineffective else 20_000_000
                injection = {
                    "sleep_start_monotonic_ns": sleep_start,
                    "sleep_end_monotonic_ns": sleep_start + sleep_ms,
                }
            boundaries.append({
                "step": step,
                "start_monotonic_ns": start,
                "end_monotonic_ns": end,
                "injection": injection,
            })
        truths[rank] = {
            "rank": rank,
            "steps": 40,
            "warmup": 5,
            "plan_nonce": plan["nonce"],
            "step_boundaries": boundaries,
        }

    observed = {"instances": []}
    predictions = {"status": "COMPLETE", "instances": []}

    def add_collective(step, status, candidate_rank=None):
        index = len(observed["instances"])
        comm_hash = 1000 + index
        function = "AllReduce"
        seq_num = index
        ranks = []
        for rank in range(4):
            boundary = truths[rank]["step_boundaries"][step]
            source_ns = boundary["start_monotonic_ns"] + 10
            if unmapped == (step, rank):
                source_ns = boundary["start_monotonic_ns"] - 25_000_000
            ranks.append({"rank": rank, "source_ns": source_ns})
        observed["instances"].append({
            "comm_hash": comm_hash,
            "function": function,
            "seq_num": seq_num,
            "ranks": ranks,
        })
        predictions["instances"].append({
            "comm_hash": comm_hash,
            "function": function,
            "seq_num": seq_num,
            "status": status,
            "rank": candidate_rank,
        })

    injection_specs = injection_specs or {}
    for step, truth_rank in EPISODES:
        specs = injection_specs.get(step, [("ROOT_CANDIDATE", truth_rank)])
        for status, candidate_rank in specs:
            add_collective(step, status, candidate_rank)
    healthy_specs = healthy_specs or {HEALTHY_STEPS[0]: [("UNKNOWN", None)]}
    for step in HEALTHY_STEPS:
        for status, candidate_rank in healthy_specs.get(step, [("UNKNOWN", None)]):
            add_collective(step, status, candidate_rank)
    return plan, observed, predictions, truths


class G201ScoringTests(unittest.TestCase):
    def test_unknown_injection_windows_are_counted_as_misses(self):
        unknown_steps = {EPISODES[0][0], EPISODES[1][0]}
        specs = {step: [("UNKNOWN", None)] for step in unknown_steps}
        result = score(*make_inputs(injection_specs=specs), HEALTHY_STEPS)
        self.assertEqual(result["top1_correct"], 6)
        self.assertEqual(result["top1_total"], 8)
        self.assertEqual(result["injection_unknown"], 2)
        self.assertEqual(result["injection_unknown_rate"], 0.25)
        self.assertEqual(result["conclusion"], "NO_GO_FOR_CURRENT_SIGNAL")

    def test_healthy_false_positives_are_aggregated_per_window(self):
        healthy = {HEALTHY_STEPS[0]: [("ROOT_CANDIDATE", 2), ("ROOT_CANDIDATE", 2)]}
        result = score(*make_inputs(healthy_specs=healthy), HEALTHY_STEPS)
        self.assertEqual(result["healthy_total"], 8)
        self.assertEqual(result["healthy_false_positives"], 1)
        self.assertEqual(result["healthy_windows"][0]["matched_collectives"], 2)
        self.assertEqual(result["healthy_windows"][0]["candidate_collectives"], 2)

    def test_conflicting_candidate_ranks_aggregate_to_unknown(self):
        conflicting = {EPISODES[0][0]: [("ROOT_CANDIDATE", 0), ("ROOT_CANDIDATE", 1)]}
        result = score(*make_inputs(injection_specs=conflicting), HEALTHY_STEPS)
        episode = result["episodes"][0]
        self.assertEqual(episode["status"], "UNKNOWN")
        self.assertIsNone(episode["rank"])
        self.assertFalse(episode["correct"])
        self.assertEqual(result["injection_unknown"], 1)

    def test_unmapped_step_boundary_makes_score_inconclusive(self):
        step, _truth_rank = EPISODES[0]
        result = score(*make_inputs(unmapped=(step, 3)), HEALTHY_STEPS)
        self.assertEqual(result["episodes"][0]["matched_collectives"], 0)
        self.assertEqual(result["conclusion"], "INCONCLUSIVE")

    def test_ineffective_injected_delay_makes_score_inconclusive(self):
        result = score(*make_inputs(ineffective=True), HEALTHY_STEPS)
        self.assertFalse(result["injection_effective"])
        self.assertEqual(result["conclusion"], "INCONCLUSIVE")

    def test_rejects_incomplete_healthy_window_denominator(self):
        with self.assertRaisesRegex(ValueError, "exactly eight"):
            score(*make_inputs(), HEALTHY_STEPS[:-1])

    def test_freeze_hash_guard_rejects_tampered_input_before_reveal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {name: root / f"{name}.json" for name in ("plan", "registration", "observed", "predictions")}
            paths["plan"].write_text(json.dumps({"nonce": "synthetic"}), encoding="utf-8")
            paths["registration"].write_text(json.dumps({"plan_sha256": sha(paths["plan"]), "healthy_steps": [35]}), encoding="utf-8")
            paths["observed"].write_text(json.dumps({"instances": []}), encoding="utf-8")
            paths["predictions"].write_text(json.dumps({"status": "COMPLETE", "instances": []}), encoding="utf-8")
            frozen = root / "freeze.json"
            freeze(paths, frozen)
            paths["predictions"].write_text(json.dumps({"status": "TAMPERED", "instances": []}), encoding="utf-8")
            argv = [
                "g2_01_score.py",
                "--plan", str(paths["plan"]),
                "--registration", str(paths["registration"]),
                "--observed", str(paths["observed"]),
                "--predictions", str(paths["predictions"]),
                "--freeze", str(frozen),
                "--truth-root", str(root / "empty-truth-root"),
                "--output", str(root / "score.json"),
            ]
            with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, "freeze hash mismatch: predictions"):
                    main()


if __name__ == "__main__":
    unittest.main()
