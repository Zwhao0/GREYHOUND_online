"""Fail-closed assertions for the archived first correction preflight attempt."""
import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORRECTION = ROOT / "docs" / "evidence" / "g1-04-correction-preflight.json"
INITIAL_SUMMARY = ROOT / "docs" / "evidence" / "g1-04-summary.json"


class G104CorrectionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.correction = json.loads(CORRECTION.read_text())
        cls.initial = json.loads(INITIAL_SUMMARY.read_text())

    def test_original_failed_gpu_summary_is_preserved_byte_for_byte(self):
        frozen = self.correction["initial_failed_gpu_run"]
        self.assertTrue(frozen["preserved"])
        digest = hashlib.sha256(INITIAL_SUMMARY.read_bytes()).hexdigest()
        self.assertEqual(digest, frozen["public_summary_sha256"])

    def test_first_control_preflight_failure_has_no_training_coverage_or_precision(self):
        report = self.correction
        self.assertEqual(report["classification"], "REAL_TWO_NODE_CPU_NETWORK_PREFLIGHT_ATTEMPT")
        self.assertEqual(report["network_attempts"], 1)
        self.assertEqual(report["additional_gpu_attempts"], 0)
        self.assertEqual(report["new_training_host_events"], 0)
        self.assertEqual(report["complete_four_stamps"], 0)
        self.assertEqual(report["preflight_proof"], "NOT_CREATED")
        self.assertIs(report["training_calibration"], False)
        self.assertEqual(report["half_width_ns"], {"n": 0, "p50": None, "p95": None, "max": None})
        self.assertEqual(report["test_classifications"]["REAL_CPU_NETWORK_PREFLIGHT"], "FAIL")
        self.assertEqual(report["test_classifications"]["GPU"], "NOT_RUN_PREFLIGHT_FAILED")
        self.assertEqual(report["test_classifications"]["MULTINODE_DDP"], "NOT_RUN_PREFLIGHT_FAILED")

        self.assertEqual(len(report["nodes"]), 2)
        for node in report["nodes"]:
            with self.subTest(role=node["role"]):
                self.assertEqual(node["control_exit"], 1)
                self.assertFalse(node["ready"])
                self.assertEqual(node["complete_four_stamps"], 0)
                self.assertFalse(node["postflight"]["gpu_or_training_started"])
                self.assertEqual(node["postflight"]["task_processes_remaining"], 0)
                self.assertEqual(node["postflight"]["own_wrapper_remaining"], 0)

        # Endpoint observations place each address on its intended host, while
        # the failed TCP start remains unresolved by this evidence.
        reference, source = report["nodes"]
        self.assertTrue(reference["endpoint_observation"]["ddp_master_is_local"])
        self.assertFalse(reference["endpoint_observation"]["control_source_is_local"])
        self.assertFalse(source["endpoint_observation"]["ddp_master_is_local"])
        self.assertTrue(source["endpoint_observation"]["control_source_is_local"])

    def test_frozen_causal_algorithm_and_attempt_source_hashes_reconcile(self):
        report = self.correction
        self.assertFalse(report["causal_algorithm_changed"])
        causal_hash = report["frozen_causal_sha256"]
        self.assertEqual(causal_hash, self.initial["source_sha256"]["g1_04_causal.py"])
        self.assertEqual(
            hashlib.sha256((ROOT / "tools" / "g1_04_causal.py").read_bytes()).hexdigest(),
            causal_hash,
        )

        hash_pattern = re.compile(r"^[0-9a-f]{64}$")
        for node in report["nodes"]:
            self.assertRegex(node["input_log_sha256"], hash_pattern)
            self.assertRegex(node["exit_sha256"], hash_pattern)
            for source, digest in node["executed_sources_sha256"].items():
                self.assertEqual(report["source_sha256"][source], digest)


if __name__ == "__main__":
    unittest.main()
