import json
import unittest

from tools.g1_03_audit import parse_audit, validate_audit


def _record() -> dict:
    return {
        "schema_version": 1,
        "run_id": "run-private",
        "rank_epoch": "epoch-private",
        "node_alias": "node-a",
        "pid": 7421,
        "comm_rank": 0,
        "comm_hash": "comm-hash-private",
        "origin_monotonic_ns": 123456,
        "clock_api": "clock_gettime(CLOCK_MONOTONIC)",
        "time_namespace": "namespace-private",
        "pid_namespace": "pid-namespace-private",
        "boot_id": "boot-private",
        "classes": {
            "Group": {
                "callback_attempted": 4,
                "pool_accepted": 4,
                "known_pool_drop": 0,
                "parent_rejected": 0,
                "guard_rejected": 0,
                "exported": 4,
                "overwritten": "UNKNOWN",
                "unit_scope": "callback-record",
                "flush": "OBSERVED_SUCCESS",
                "source": "upstream profiler callback source",
            },
            "Coll": {
                "callback_attempted": 4,
                "pool_accepted": 3,
                "known_pool_drop": 1,
                "parent_rejected": 0,
                "guard_rejected": 0,
                "exported": 3,
                "overwritten": "UNKNOWN",
                "unit_scope": "callback-record",
                "flush": "OBSERVED_SUCCESS",
                "source": "upstream profiler callback source",
            },
            "KernelCh": {
                "callback_attempted": 4,
                "pool_accepted": 4,
                "known_pool_drop": 0,
                "parent_rejected": 0,
                "guard_rejected": 0,
                "exported": 4,
                "overwritten": "UNKNOWN",
                "flush": "UNKNOWN",
                "source": "timer ring callback source",
            },
        },
        "export": {"file_open_ok": True, "write_ok": True, "close_ok": True, "status": "OK"},
    }


class G103AuditTests(unittest.TestCase):
    def test_json_input_is_validated_and_private_identity_is_redacted(self):
        record = _record()
        report = parse_audit(json.dumps(record))
        encoded = json.dumps(report)
        self.assertEqual(report["schema_status"], "OBSERVED")
        self.assertEqual(report["identity"]["node_alias"], "node-a")
        self.assertEqual(report["identity"]["clock_api"], "CLOCK_MONOTONIC")
        self.assertEqual(report["classes"]["Group"]["flush_status"], "OBSERVED_SUCCESS")
        self.assertFalse(report["callback_attempted_is_nccl_total"])
        self.assertEqual(report["mapping_status"], "NOT_CHECKED")
        for private in ("run-private", "epoch-private", "7421", "comm-hash-private", "namespace-private",
                        "pid-namespace-private", "boot-private"):
            self.assertNotIn(private, encoded)
        self.assertNotIn("upstream profiler callback source", encoded)

    def test_simulated_overflow_keeps_ring_overwrite_unknown(self):
        record = _record()
        record["classes"]["Coll"].update({
            "callback_attempted": 12,
            "pool_accepted": 8,
            "known_pool_drop": 4,
            "exported": 8,
            "overwritten": "UNKNOWN",
        })
        report = validate_audit(record)["classes"]
        coll = report["Coll"]
        self.assertEqual(coll["callback_conservation"], "OBSERVED")
        self.assertEqual(coll["exported_le_accepted"], "OBSERVED")
        self.assertEqual(coll["counters"]["overwritten"], "UNKNOWN")
        self.assertEqual(report["KernelCh"]["callback_conservation"], "OBSERVED")

    def test_missing_counters_remain_unknown_and_absent_class_is_missing(self):
        record = _record()
        record["classes"]["Group"] = {"callback_attempted": 4, "source": "callback"}
        del record["classes"]["KernelCh"]
        report = validate_audit(record)["classes"]
        self.assertEqual(report["Group"]["status"], "OBSERVED")
        self.assertEqual(report["Group"]["counters"]["pool_accepted"], "UNKNOWN")
        self.assertEqual(report["Group"]["counter_status"]["pool_accepted"], "MISSING")
        self.assertEqual(report["Group"]["callback_conservation"], "UNKNOWN")
        self.assertEqual(report["KernelCh"]["status"], "MISSING")

    def test_failed_write_is_visible_as_export_failure(self):
        record = _record()
        record["export"]["write_ok"] = False
        report = validate_audit(record)
        self.assertEqual(report["export"]["status"], "FAILED")
        self.assertEqual(report["classes"]["Coll"]["counters"]["exported"], "UNKNOWN")
        self.assertIn("EXPORT_WRITE_FAILED", report["issues"])

    def test_mapping_mismatch_checks_run_epoch_rank_and_namespace(self):
        record = _record()
        expected = {
            "run_id": "other-run",
            "rank_epoch": "other-epoch",
            "comm_rank": 1,
            "time_namespace": "other-namespace",
            "pid_namespace": "other-pid-namespace",
        }
        report = validate_audit(record, expected)
        self.assertEqual(report["mapping_status"], "MISMATCH")
        self.assertEqual(report["mapping_checks"]["run_id"], "MISMATCH")
        self.assertEqual(report["mapping_checks"]["rank_epoch"], "MISMATCH")
        self.assertEqual(report["mapping_checks"]["comm_rank"], "MISMATCH")
        self.assertEqual(report["mapping_checks"]["time_namespace"], "MISMATCH")
        self.assertEqual(report["mapping_checks"]["pid_namespace"], "MISMATCH")

    def test_conservation_mismatch_and_scope_gated_export_bound(self):
        record = _record()
        record["classes"]["Group"].update({"callback_attempted": 10, "pool_accepted": 8,
                                            "known_pool_drop": 1, "exported": 9})
        report = validate_audit(record)["classes"]["Group"]
        self.assertEqual(report["callback_conservation"], "MISMATCH")
        self.assertEqual(report["exported_le_accepted"], "MISMATCH")
        record["classes"]["Group"]["unit_scopes"] = {
            "pool_accepted": "callback-record", "exported": "timer-event"
        }
        self.assertEqual(validate_audit(record)["classes"]["Group"]["exported_le_accepted"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
