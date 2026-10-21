"""Public evidence checks for the corrected G1-04 capture."""
import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "docs" / "evidence" / "g1-04-correction-summary.json"
PREFLIGHT_PATH = ROOT / "docs" / "evidence" / "g1-04-correction-preflight.json"
INITIAL_SUMMARY_PATH = ROOT / "docs" / "evidence" / "g1-04-summary.json"


class G104CorrectionCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads(SUMMARY_PATH.read_text())
        cls.preflight = json.loads(PREFLIGHT_PATH.read_text())
        cls.initial = json.loads(INITIAL_SUMMARY_PATH.read_text())

    def test_each_public_event_interval_recomputes_from_strict_stamps(self):
        report = self.summary
        events = report["events"]
        samples = report["control"]["selected_four_stamps_ns"]
        self.assertEqual(report["unit"], "ns")
        self.assertEqual(len(events), 280)
        self.assertEqual(len(samples), 50)

        mapped = 0
        local = 0
        for event in events:
            with self.subTest(rank=event["rank"], seq=event["seq"]):
                self.assertEqual(event["status"], "BOUNDED")
                self.assertTrue(event["coverage"])
                self.assertEqual(event["unit"], "ns")
                source_ns = event["source_ns"]
                error_ns = event["representation_error_ns"]
                interval = event["reference_interval_ns"]
                self.assertIsInstance(source_ns, int)
                self.assertIsInstance(error_ns, int)
                self.assertGreaterEqual(interval[0], 0)

                if not event["evidence_indices"]:
                    local += 1
                    expected = [source_ns - error_ns, source_ns + error_ns]
                    self.assertEqual(interval, expected)
                    self.assertEqual(event["half_width_ns"], error_ns)
                    continue

                mapped += 1
                low = source_ns - error_ns
                high = source_ns + error_ns
                left_candidates = [sample for sample in samples if sample["t2"] < low]
                right_candidates = [sample for sample in samples if high < sample["t3"]]
                self.assertTrue(left_candidates)
                self.assertTrue(right_candidates)

                # The bounds use the last valid lower exchange and first valid
                # upper exchange. The inequalities are deliberately strict.
                left = max(left_candidates, key=lambda sample: sample["t1"])
                right = min(right_candidates, key=lambda sample: sample["t4"])
                expected = [
                    max(sample["t1"] for sample in left_candidates),
                    min(sample["t4"] for sample in right_candidates),
                ]
                self.assertLessEqual(expected[0], expected[1])
                self.assertEqual(interval, expected)
                expected_indices = (
                    [left["index"]]
                    if left["index"] == right["index"]
                    else [left["index"], right["index"]]
                )
                self.assertEqual(event["evidence_indices"], expected_indices)
                self.assertEqual(
                    event["half_width_ns"],
                    (expected[1] - expected[0] + 1) // 2,
                )

        self.assertEqual(mapped, 140)
        self.assertEqual(local, 140)
        self.assertEqual(report["source_node_summary"]["events"], mapped)

    def test_reported_width_coverage_rank_and_order_statistics(self):
        report = self.summary
        self.assertEqual(report["classification"], "REAL_HEALTHY_MULTINODE_TRACE_AND_CONTROL_EXCHANGES")
        self.assertEqual(report["candidate_status"], "SCOPED_GATE_REVIEW_CANDIDATE")
        self.assertEqual(report["summary"]["events"], 280)
        self.assertEqual(report["summary"]["covered"], 280)
        self.assertEqual(report["summary"]["bounded"], 280)
        self.assertEqual(report["summary"]["unsafe_fraction"], 0.0)
        self.assertEqual(
            report["summary"]["half_width_ns"],
            {"n": 280, "p50": 53182.5, "p95": 524646.0, "max": 583573},
        )
        self.assertEqual(
            report["source_node_summary"]["half_width_ns"],
            {"n": 140, "p50": 511319.0, "p95": 526649.0, "max": 583573},
        )
        self.assertEqual(
            report["source_node_summary"]["budget_coverage"],
            {"1000000": 1.0, "5000000": 1.0, "10000000": 1.0},
        )

        expected_ranks = {
            0: (70, 4000.0, 4000.0, 4000),
            1: (70, 4000.0, 4000.0, 4000),
            2: (70, 511304.0, 525694.0, 583573),
            3: (70, 511334.0, 526649.0, 583173),
        }
        self.assertEqual(len(report["ranks"]), 4)
        for rank_record in report["ranks"]:
            with self.subTest(rank=rank_record["rank"]):
                rank = rank_record["rank"]
                count, p50, p95, max_width = expected_ranks[rank]
                summary = rank_record["summary"]
                self.assertEqual(summary["events"], count)
                self.assertEqual(summary["covered"], count)
                self.assertEqual(summary["bounded"], count)
                self.assertEqual(summary["unsafe_fraction"], 0.0)
                self.assertEqual(
                    summary["half_width_ns"],
                    {"n": count, "p50": p50, "p95": p95, "max": max_width},
                )
                self.assertEqual(
                    summary["budget_coverage"],
                    {"1000000": 1.0, "5000000": 1.0, "10000000": 1.0},
                )
                self.assertTrue(rank_record["control_covers_audited_active_window"])

        eligible = report["eligible_four_rank_instances"]
        all_reduce = [row for row in eligible if row["op"] == "AllReduce"]
        self.assertEqual(len(eligible), 70)
        self.assertEqual(len(all_reduce), 69)
        self.assertTrue(all(b["seq"] == a["seq"] + 1 for a, b in zip(all_reduce, all_reduce[1:])))
        self.assertEqual(report["continuous_four_rank_1ms_max_instances"], 69)
        self.assertEqual(
            report["cross_node_matched_pair_interval_order"],
            {"AFTER": 68, "BEFORE": 16, "OVERLAP_OR_UNKNOWN": 196},
        )

    def test_public_hashes_runtime_and_original_failure_remain_auditable(self):
        report = self.summary
        digest_pattern = re.compile(r"^[0-9a-f]{64}$")
        self.assertEqual(len(report["ranks"]), 4)
        trace_hashes = [row["input_trace_sha256"] for row in report["ranks"]]
        audit_hashes = [row["input_audit_sha256"] for row in report["ranks"]]
        self.assertEqual(len(set(trace_hashes)), 4)
        self.assertEqual(len(set(audit_hashes)), 4)
        for digest in trace_hashes + audit_hashes:
            self.assertRegex(digest, digest_pattern)

        control_hashes = list(report["control"]["input_sha256"].values())
        self.assertEqual(len(control_hashes), 2)
        self.assertEqual(len(set(control_hashes)), 2)
        for digest in control_hashes:
            self.assertRegex(digest, digest_pattern)
        self.assertEqual(report["control"]["status"], "BOUNDED")
        self.assertTrue(report["control"]["complete"])
        self.assertEqual(report["control"]["count"], 106637)

        executed_sources = report["executed_source_sha256"]
        self.assertEqual(len(executed_sources), 2)
        self.assertTrue(all(len(sources) == 7 for sources in executed_sources.values()))
        for sources in executed_sources.values():
            for digest in sources.values():
                self.assertRegex(digest, digest_pattern)

        # Runtime rows retain the measured GPU steps and resolved library
        # identities needed to check the public summary against raw evidence.
        self.assertEqual(len(report["runtime"]), 4)
        self.assertEqual({row["rank"] for row in report["runtime"]}, {0, 1, 2, 3})
        for runtime in report["runtime"]:
            self.assertEqual(len(runtime["gpu_step_ms"]), 30)
            self.assertEqual(len(runtime["dsos"]), 3)
            for dso in runtime["dsos"]:
                self.assertRegex(dso["sha256"], digest_pattern)

        preflight = self.preflight
        frozen = preflight["initial_failed_gpu_run"]
        self.assertTrue(frozen["preserved"])
        self.assertEqual(
            hashlib.sha256(INITIAL_SUMMARY_PATH.read_bytes()).hexdigest(),
            frozen["public_summary_sha256"],
        )
        causal_hash = preflight["frozen_causal_sha256"]
        self.assertEqual(causal_hash, self.initial["source_sha256"]["g1_04_causal.py"])
        self.assertEqual(causal_hash, report["source_sha256"]["g1_04_causal.py"])
        self.assertEqual(
            hashlib.sha256((ROOT / "tools" / "g1_04_causal.py").read_bytes()).hexdigest(),
            causal_hash,
        )


if __name__ == "__main__":
    unittest.main()
