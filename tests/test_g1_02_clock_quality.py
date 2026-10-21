"""CPU synthetic fixtures only: no clock sampling/calibration/GPU evidence."""
import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.g1_02_clock_quality import (
    assess_clock_quality, compare_fixture_times, evaluate_four_timestamp_fixture,
)


def exchange():
    return {
        "classification": "CPU_SYNTHETIC", "transport": "INDEPENDENT_CONTROL",
        "reference": {"domain": "HOST_MONOTONIC", "domain_id": "reference-process", "epoch": "run-a", "unit": "us"},
        "source": {"domain": "HOST_MONOTONIC", "domain_id": "source-process", "epoch": "run-a", "unit": "us"},
        "t1": 100, "t2": 112, "t3": 114, "t4": 108,
        "nonnegative_one_way_delay_assumed": True, "timestamp_error_bound": 0,
        "max_uncertainty": 100, "drift_bound_ppm": 0, "valid_from": 0, "valid_until": 1000,
    }


def instant(contract, identity, timestamp):
    return {**contract[identity], "timestamp": timestamp}


class ClockQualityTests(unittest.TestCase):
    def test_existing_domains_never_cross_rank_comparable(self):
        for domain in ("PROCESS_CLOCK_MONOTONIC_RELATIVE", "GPU_GLOBALTIMER", "CUDA_EVENT_DURATION", "UNKNOWN"):
            with self.subTest(domain=domain):
                result = assess_clock_quality({"domain": domain, "unit": "us", "calibration": "CALIBRATED"})
                self.assertEqual(result["status"], "UNSAFE")
                self.assertEqual(result["calibration"], "UNKNOWN")
                self.assertFalse(result["actual_cross_rank_comparable"])
                self.assertEqual(result["epoch"], "UNKNOWN")
                self.assertIn("593de54", result["provenance"]["host"])

    def test_invalid_existing_record_fails_closed(self):
        for record in (None, [], {"clock": []}):
            self.assertEqual(assess_clock_quality(record)["status"], "UNSAFE")

    def test_asymmetric_delays_bound_offset_without_midpoint_claim(self):
        # Actual offset=10, forward delay=2, reverse delay=4.
        result = evaluate_four_timestamp_fixture(exchange())
        self.assertEqual(result["status"], "BOUNDED")
        low, high = result["offset_source_minus_reference"]
        self.assertLessEqual(low, 6)
        self.assertGreaterEqual(high, 12)
        self.assertLess(low, 10)
        self.assertGreater(high, 10)
        self.assertEqual(result["calibration"], "UNKNOWN")
        self.assertFalse(result["actual_cross_rank_comparable"])
        json.dumps(result, allow_nan=False)

    def test_each_missing_input_is_unsafe(self):
        for key in (key for key in exchange() if key != "max_uncertainty"):
            fixture = exchange()
            del fixture[key]
            with self.subTest(key=key):
                self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_all_nonnumeric_nonfinite_inputs_unsafe(self):
        for key in ("t1", "t2", "t3", "t4", "timestamp_error_bound", "drift_bound_ppm", "valid_from", "valid_until"):
            for value in (None, True, "1", math.nan, math.inf, -math.inf, 10 ** 10000):
                fixture = exchange()
                fixture[key] = value
                with self.subTest(key=key, kind=type(value).__name__):
                    self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_unknown_identities_and_wrong_units_unsafe(self):
        for side in ("reference", "source"):
            for key in ("domain", "domain_id", "epoch", "unit"):
                fixture = exchange()
                fixture[side][key] = "UNKNOWN"
                self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")
        for change in ({"unit": "ns"}, {"domain": "GPU_GLOBALTIMER"}, {"domain_id": "reference-process"}):
            fixture = exchange()
            fixture["source"].update(change)
            self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_real_evidence_or_world_control_is_not_fixture_calibration(self):
        for key, value in (("classification", "MULTINODE"), ("transport", "TRAINING_WORLD"),
                           ("nonnegative_one_way_delay_assumed", False), ("nonnegative_one_way_delay_assumed", "true")):
            fixture = exchange()
            fixture[key] = value
            self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_noncausal_exchange_and_window_unsafe(self):
        for changes in ({"t4": 99}, {"t3": 111}, {"t3": 121},
                        {"valid_from": 101}, {"valid_until": 107},
                        {"drift_bound_ppm": -1}, {"drift_bound_ppm": 1000000},
                        {"timestamp_error_bound": -1}):
            fixture = exchange()
            fixture.update(changes)
            self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_drift_and_errors_widen_interval(self):
        fixture = exchange()
        fixture.update(drift_bound_ppm=1000, timestamp_error_bound=1)
        low, high = evaluate_four_timestamp_fixture(fixture)["offset_source_minus_reference"]
        self.assertLessEqual(low, 6 - 2 - .910)
        self.assertGreaterEqual(high, 12 + 2 + .910)
        baseline = evaluate_four_timestamp_fixture(fixture)
        fixture["valid_until"] = 2000
        wider = evaluate_four_timestamp_fixture(fixture)
        self.assertLess(wider["offset_source_minus_reference"][0], baseline["offset_source_minus_reference"][0])

    def test_interval_comparison_excludes_or_preserves_zero(self):
        fixture = exchange()
        for timestamp, expected in ((220, "SECOND_AFTER_FIRST"), (205, "SECOND_BEFORE_FIRST"), (210, "UNKNOWN")):
            result = compare_fixture_times(instant(fixture, "reference", 200), instant(fixture, "source", timestamp), fixture)
            self.assertEqual(result["status"], "BOUNDED")
            self.assertEqual(result["order"], expected)
            self.assertEqual(result["calibration"], "UNKNOWN")

    def test_comparison_mismatch_or_expired_mapping_unsafe(self):
        fixture = exchange()
        first, second = instant(fixture, "reference", 200), instant(fixture, "source", 210)
        for side in (0, 1):
            for key in ("domain", "domain_id", "epoch", "unit"):
                pair = copy.deepcopy([first, second])
                pair[side][key] = "wrong"
                self.assertEqual(compare_fixture_times(*pair, fixture)["status"], "UNSAFE")
        for a, b in ((-1, 210), (200, 1010), (200, math.nan)):
            self.assertEqual(compare_fixture_times(instant(fixture, "reference", a), instant(fixture, "source", b), fixture)["status"], "UNSAFE")

    def test_timestamp_error_is_included_on_both_comparison_sides(self):
        fixture = exchange()
        fixture["timestamp_error_bound"] = 1
        result = compare_fixture_times(instant(fixture, "reference", 200), instant(fixture, "source", 220), fixture)
        low, high = result["second_minus_first"]
        self.assertLessEqual(low, 4)
        self.assertGreaterEqual(high, 18)
        self.assertEqual(compare_fixture_times(instant(fixture, "reference", 0), instant(fixture, "source", 210), fixture)["status"], "UNSAFE")

    def test_comparison_requires_sufficient_explicit_uncertainty_budget(self):
        fixture = exchange()
        pair = (instant(fixture, "reference", 200), instant(fixture, "source", 220))
        for budget in (None, -1, 0, 2, math.inf, True):
            fixture["max_uncertainty"] = budget
            self.assertEqual(compare_fixture_times(*pair, fixture)["status"], "UNSAFE")
        fixture["max_uncertainty"] = 4
        self.assertEqual(compare_fixture_times(*pair, fixture)["order"], "SECOND_AFTER_FIRST")
        # Zero RTT fixture gives exact offset=10 mathematically. Still include
        # outward JSON rounding in the conservative uncertainty budget.
        fixture.update(t1=100, t2=110, t3=110, t4=100, max_uncertainty=1e-10)
        self.assertEqual(compare_fixture_times(*pair, fixture)["order"], "SECOND_AFTER_FIRST")
        fixture.update(t1=100, t2=120, t3=120, t4=120, max_uncertainty=4)
        self.assertEqual(compare_fixture_times(*pair, fixture)["status"], "UNSAFE")

    def test_extreme_derived_bounds_do_not_emit_infinity(self):
        fixture = exchange()
        fixture.update(t1=-1e308, t2=-1e308, t3=1e308, t4=1e308,
                       valid_from=-1e308, valid_until=1e308, timestamp_error_bound=1e308)
        self.assertEqual(evaluate_four_timestamp_fixture(fixture)["status"], "UNSAFE")

    def test_cli_fixture_and_unknown_failure(self):
        script = Path(__file__).parents[1] / "tools" / "g1_02_clock_quality.py"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(exchange()), encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(path), "--fixture"], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["classification"], "CPU_SYNTHETIC")
            path.write_text("{}", encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "UNSAFE")


if __name__ == "__main__":
    unittest.main()
