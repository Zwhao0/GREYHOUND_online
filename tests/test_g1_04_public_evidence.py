"""Fail-closed checks for the public G1-04 healthy-run evidence summary."""
import json
import unittest
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "g1-04-summary.json"


class G104PublicEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(EVIDENCE.read_text())

    def test_failed_control_capture_keeps_all_host_mappings_unknown(self):
        report = self.report
        control = report["control"]
        self.assertEqual(control["status"], "UNSAFE_TO_SUBTRACT")
        self.assertFalse(control["complete"])
        self.assertEqual(control["count"], 0)
        self.assertIsNone(control["reference_window_ns"])
        self.assertIsNone(control["source_window_ns"])
        self.assertEqual(control["selected_four_stamps_ns"], [])
        self.assertIn("CONTROL_CAPTURE_FAILED", " ".join(control["reasons"]))

        events = report["events"]
        self.assertEqual(len(events), 280)
        for event in events:
            with self.subTest(rank=event["rank"], seq=event["seq"]):
                self.assertEqual(event["status"], "UNSAFE_TO_SUBTRACT")
                self.assertFalse(event["coverage"])
                self.assertIsNone(event["reference_interval_ns"])
                self.assertIsNone(event["half_width_ns"])
                self.assertEqual(event["evidence_indices"], [])
                self.assertTrue(event["reasons"])

        summary = report["summary"]
        self.assertEqual(summary["events"], 280)
        self.assertEqual(summary["covered"], 0)
        self.assertEqual(summary["bounded"], 0)
        self.assertEqual(summary["unsafe_fraction"], 1.0)
        self.assertEqual(summary["half_width_ns"], {"n": 0, "p50": None, "p95": None, "max": None})
        self.assertTrue(all(value == 0.0 for value in summary["budget_coverage"].values()))

    def test_trace_matching_counts_reconcile_without_claiming_host_order(self):
        report = self.report
        matching = report["matching_summary"]
        self.assertEqual(matching["expected_ranks"], 4)
        self.assertEqual(matching["parsed_rank_traces"], 4)
        self.assertEqual(matching["collective_keys"], 70)
        self.assertEqual(matching["matched"], 70)
        self.assertEqual(matching["missing_rank"], 0)
        self.assertEqual(matching["duplicates"], 0)
        self.assertEqual(matching["metadata_conflicts"], 0)

        self.assertEqual(len(report["ranks"]), 4)
        for rank in report["ranks"]:
            self.assertEqual(rank["summary"]["events"], 70)
            self.assertEqual(rank["summary"]["covered"], 0)
            self.assertEqual(rank["summary"]["bounded"], 0)
            self.assertEqual(rank["identity_binding"], "TRACE_TRAINING_PID_ONLY_CONTROL_UNAVAILABLE")
        self.assertEqual(report["cross_node_matched_pair_interval_order"], {"OVERLAP_OR_UNKNOWN": 280})
        self.assertEqual(report["eligible_four_rank_instances"], [])
        self.assertEqual(report["continuous_four_rank_1ms_max_instances"], 0)

    def test_healthy_training_and_export_facts_do_not_upgrade_mapping(self):
        report = self.report
        self.assertEqual(report["candidate_status"], "PARTIAL")
        self.assertEqual(report["test_classifications"]["GPU"], "HEALTHY_DDP_ONLY_PASS")
        self.assertEqual(report["test_classifications"]["MULTINODE"], "HEALTHY_4RANK_ONLY_PASS")
        self.assertEqual(report["test_classifications"]["REAL_HOST_MAPPING"], "FAIL")
        self.assertEqual(len(report["runtime"]), 4)
        self.assertTrue(all(len(rank["gpu_step_ms"]) == 30 for rank in report["runtime"]))

        self.assertEqual(len(report["resource_exit"]), 2)
        for node in report["resource_exit"]:
            self.assertEqual(node["training_exit"], 0)
            self.assertEqual(node["control_exit"], 1)
            self.assertEqual(node["task_processes_remaining"], 0)

        for rank in report["ranks"]:
            audit = rank["collector_audit"]
            self.assertEqual(audit["export"]["status"], "OBSERVED_SUCCESS")
            self.assertFalse(audit["callback_attempted_is_nccl_total"])
            coll = audit["classes"]["Coll"]
            self.assertEqual(coll["callback_conservation"], "OBSERVED")
            self.assertEqual(coll["counters"]["overwritten"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
