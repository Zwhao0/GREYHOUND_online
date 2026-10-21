"""CPU fixtures for causal host-clock interval mapping; no GPU/network proof."""
import copy
import unittest

from tools.g1_04_causal import compare_intervals, map_event, validate_capture


CLASSIFICATION = "REAL_HOST_CONTROL"
TRANSPORT = "INDEPENDENT_TCP_CONTROL"


def identity(node, pid, suffix):
    return {
        "run": "run-a",
        "epoch": "epoch-a",
        "node": node,
        "pid": pid,
        "time_namespace": f"time:[{suffix}]",
        "pid_namespace": f"pid:[{suffix}]",
        "boot_id": f"boot-{node}",
        "clock_api": "clock_gettime(CLOCK_MONOTONIC)",
        "resolution_ns": 1,
    }


def captures():
    """Three continuous four-stamp exchanges with a wide source-clock gap."""
    reference = identity("node-ref", 1001, 1)
    source = identity("node-src", 1002, 2)
    exchanges = [
        {"index": 0, "t1": 100_000, "t2": 200_000, "t3": 210_000, "t4": 110_000},
        {"index": 1, "t1": 300_000, "t2": 400_000, "t3": 410_000, "t4": 310_000},
        {"index": 2, "t1": 500_000, "t2": 600_000, "t3": 610_000, "t4": 510_000},
    ]
    client = {
        "schema": "g1-04-host-control-v1",
        "classification": CLASSIFICATION,
        "transport": TRANSPORT,
        "phase": "continuous",
        "unit": "ns",
        "complete": True,
        "count": len(exchanges),
        "reference": reference,
        "source": source,
        "exchanges": copy.deepcopy(exchanges),
    }
    server = {
        "schema": "g1-04-host-control-v1",
        "classification": CLASSIFICATION,
        "transport": TRANSPORT,
        "phase": "continuous",
        "unit": "ns",
        "complete": True,
        "count": len(exchanges),
        "source": copy.deepcopy(source),
        "exchanges": [
            {key: sample[key] for key in ("index", "t1", "t2", "t3")}
            for sample in exchanges
        ],
    }
    return client, server


def audits(client=None):
    client = client or captures()[0]
    reference = {
        **client["reference"],
        "origin_monotonic_ns": 50_000,
        "active_until_monotonic_ns": 700_000,
        "origin_mapping_error_ns": 4_000,
    }
    source = {
        **client["source"],
        "origin_monotonic_ns": 50_000,
        "active_until_monotonic_ns": 700_000,
        "origin_mapping_error_ns": 4_000,
    }
    return [reference, source]


class G104CausalTests(unittest.TestCase):
    def test_valid_capture_maps_control_segment_and_reports_provenance(self):
        client, server = captures()
        quality = validate_capture(client, server, audits(client))

        self.assertEqual(quality["status"], "BOUNDED")
        mapped = map_event(quality, audits(client)[1], 205_000)
        self.assertEqual(mapped["status"], "BOUNDED")
        self.assertEqual(mapped["reference_interval_ns"], [100_000, 110_000])
        self.assertEqual(mapped["half_width_ns"], 5_000)
        self.assertEqual(mapped["evidence_indices"], [0])
        self.assertEqual(mapped["reasons"], [])

    def test_event_in_gap_uses_conservative_neighboring_causal_bracket(self):
        client, server = captures()
        quality = validate_capture(client, server, audits(client))

        # 250us lies after exchange 0's source send and before exchange 1's
        # source receive. It is bracketed by reference send 0 and receive 1.
        mapped = map_event(quality, audits(client)[1], 250_000)
        self.assertEqual(mapped["status"], "BOUNDED")
        self.assertEqual(mapped["reference_interval_ns"], [100_000, 310_000])
        self.assertEqual(mapped["half_width_ns"], 105_000)
        self.assertEqual(mapped["evidence_indices"], [0, 1])

    def test_event_without_causal_coverage_fails_closed(self):
        client, server = captures()
        quality = validate_capture(client, server, audits(client))

        mapped = map_event(quality, audits(client)[1], 150_000)
        self.assertEqual(mapped["status"], "UNSAFE_TO_SUBTRACT")
        self.assertIsNone(mapped["reference_interval_ns"])
        self.assertTrue(mapped["reasons"])

    def test_error_band_must_remain_strictly_inside_the_sampled_coverage(self):
        client, server = captures()
        quality = validate_capture(client, server, audits(client))

        # The nominal timestamp is in the segment, but the uncertainty touches
        # its send endpoint. Equal monotonic reads do not prove ordering.
        mapped = map_event(quality, audits(client)[1], 205_000, error_ns=5_000)
        self.assertEqual(mapped["status"], "UNSAFE_TO_SUBTRACT")
        self.assertIsNone(mapped["reference_interval_ns"])

    def test_missing_or_lost_server_control_exchange_is_unsafe(self):
        client, server = captures()
        server["exchanges"].pop(1)
        server["count"] -= 1

        quality = validate_capture(client, server, audits(client))
        self.assertEqual(quality["status"], "UNSAFE_TO_SUBTRACT")
        self.assertTrue(quality["reasons"])

    def test_out_of_order_control_index_or_source_clock_rollback_is_unsafe(self):
        for corruption in ("index", "rollback"):
            with self.subTest(corruption=corruption):
                client, server = captures()
                if corruption == "index":
                    client["exchanges"][1]["index"] = 4
                    server["exchanges"][1]["index"] = 4
                else:
                    client["exchanges"][1]["t2"] = 190_000
                    client["exchanges"][1]["t3"] = 195_000
                    server["exchanges"][1]["t2"] = 190_000
                    server["exchanges"][1]["t3"] = 195_000

                quality = validate_capture(client, server, audits(client))
                self.assertEqual(quality["status"], "UNSAFE_TO_SUBTRACT")
                self.assertTrue(quality["reasons"])

    def test_training_pid_must_match_validated_audit_and_namespace_mismatch_is_unsafe(self):
        client, server = captures()
        evidence = audits(client)
        quality = validate_capture(client, server, evidence)
        changed_pid = copy.deepcopy(evidence[1])
        changed_pid["pid"] += 1
        mapped = map_event(quality, changed_pid, 205_000)
        self.assertEqual(mapped["status"], "UNSAFE_TO_SUBTRACT")
        self.assertIsNone(mapped["reference_interval_ns"])

        evidence[1]["time_namespace"] = "time:[99]"
        mismatched_namespace = validate_capture(client, server, evidence)
        self.assertEqual(mismatched_namespace["status"], "UNSAFE_TO_SUBTRACT")
        self.assertTrue(mismatched_namespace["reasons"])

    def test_unit_or_capture_identity_mismatch_is_unsafe(self):
        for corruption in ("unit", "namespace"):
            with self.subTest(corruption=corruption):
                client, server = captures()
                if corruption == "unit":
                    server["unit"] = "us"
                else:
                    server["source"]["time_namespace"] = "time:[3]"
                quality = validate_capture(client, server, audits(client))
                self.assertEqual(quality["status"], "UNSAFE_TO_SUBTRACT")

    def test_mapping_wider_than_explicit_budget_is_unsafe(self):
        client, server = captures()
        quality = validate_capture(client, server, audits(client))

        mapped = map_event(quality, audits(client)[1], 250_000, budget_ns=100_000)
        self.assertEqual(mapped["status"], "UNSAFE_TO_SUBTRACT")
        self.assertEqual(mapped["reference_interval_ns"], [100_000, 310_000])
        self.assertGreater(mapped["half_width_ns"], 100_000)
        self.assertTrue(mapped["reasons"])

    def test_incomplete_and_unknown_origin_error_are_rejected(self):
        for key in ('complete', 'origin_mapping_error_ns'):
            client, server = captures()
            evidence = audits(client)
            if key == 'complete':
                client.pop(key)
            else:
                evidence[1].pop(key)
            self.assertEqual(validate_capture(client, server, evidence)['status'], 'UNSAFE_TO_SUBTRACT')

    def test_caller_cannot_shrink_audited_error_and_reference_maps_locally(self):
        client, server = captures()
        evidence = audits(client)
        quality = validate_capture(client, server, evidence)
        self.assertEqual(map_event(quality, evidence[1], 205_000, error_ns=0)['status'], 'UNSAFE_TO_SUBTRACT')
        mapped = map_event(quality, evidence[0], 205_000)
        self.assertEqual(mapped['reference_interval_ns'], [201_000, 209_000])
        self.assertEqual(mapped['half_width_ns'], 4000)

    def test_interval_comparison_requires_strict_nonoverlap_and_bounded_inputs(self):
        clock = ["run-a", "epoch-a", "node-ref"]
        before = {"status": "BOUNDED", "unit": "ns", "reference_interval_ns": [10, 20], "reference_clock": clock}
        after = {"status": "BOUNDED", "unit": "ns", "reference_interval_ns": [21, 30], "reference_clock": clock}
        overlapping = {"status": "BOUNDED", "unit": "ns", "reference_interval_ns": [20, 30], "reference_clock": clock}
        equal = {"status": "BOUNDED", "unit": "ns", "reference_interval_ns": [10, 20], "reference_clock": clock}
        unsafe = {"status": "UNSAFE_TO_SUBTRACT", "unit": "ns", "reference_interval_ns": [31, 40], "reference_clock": clock}
        other_clock = {"status": "BOUNDED", "unit": "ns", "reference_interval_ns": [21, 30],
                       "reference_clock": ["run-a", "epoch-a", "node-other"]}

        self.assertEqual(compare_intervals(before, after), "BEFORE")
        self.assertEqual(compare_intervals(after, before), "AFTER")
        self.assertEqual(compare_intervals(before, overlapping), "OVERLAP_OR_UNKNOWN")
        self.assertEqual(compare_intervals(before, equal), "OVERLAP_OR_UNKNOWN")
        self.assertEqual(compare_intervals(before, unsafe), "OVERLAP_OR_UNKNOWN")
        self.assertEqual(compare_intervals(before, other_clock), "OVERLAP_OR_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
