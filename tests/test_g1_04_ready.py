"""CPU-only readiness marker and first-exchange handshake fixtures."""
import copy
import hashlib
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from g1_04_control import check_peer, publish_ready, run
from tools.g1_04_preflight import verify_pair, verify_ready


COLLECTOR = Path(__file__).resolve().parents[1] / "tools" / "g1_04_control.py"
HOST_HELPER = COLLECTOR.with_name("g1_03_host_clock.py")


def identity(node, run_id="run-cpu", epoch="epoch-cpu", pid=None):
    suffix = "a" if node == "node-a" else "b"
    return {
        "run": run_id,
        "epoch": epoch,
        "node": node,
        "pid": os.getpid() if pid is None else pid,
        "pid_namespace": f"pid:[{suffix}]",
        "time_namespace": f"time:[{suffix}]",
        "boot_id": f"boot-{suffix}",
        "clock_api": "clock_gettime(CLOCK_MONOTONIC)",
        "resolution_ns": 1,
    }


def proof_for(reference, source):
    return {
        "status": "PASS",
        "classification": "CPU_NETWORK_ONLY",
        "training_calibration": False,
        "reference": copy.deepcopy(reference),
        "source": copy.deepcopy(source),
        "collector_sha256": hashlib.sha256(COLLECTOR.read_bytes()).hexdigest(),
        "host_helper_sha256": hashlib.sha256(HOST_HELPER.read_bytes()).hexdigest(),
    }


def marker_for(own, peer):
    return {
        "status": "CONTROL_READY",
        "unit": "ns",
        "self": copy.deepcopy(own),
        "peer": copy.deepcopy(peer),
        "first_exchange": {"index": 0, "t1": 10, "t2": 20, "t3": 21, "t4": 11},
        "process_start_ticks": None,
    }


class G104ReadyTests(unittest.TestCase):
    def verify_cpu_ready(self, marker, proof, node):
        # Synthetic identities cannot be checked against Linux /proc on every
        # developer machine. Patch only that host-specific check in CPU tests.
        with patch("tools.g1_04_preflight.verify_live_process") as live_check:
            result = verify_ready(marker, proof, "run-cpu", "epoch-cpu", node, COLLECTOR)
            live_check.assert_called_once_with(marker["self"], marker.get("process_start_ticks"))
        return result

    def test_stale_marker_publication_is_atomic_and_never_overwrites(self):
        own = identity("node-a")
        peer = identity("node-b")
        row = {"index": 0, "t1": 10, "t2": 20, "t3": 21, "t4": 11}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ready.json"
            previous = b'{"status":"OLD_SESSION"}\n'
            path.write_bytes(previous)

            with self.assertRaises(FileExistsError):
                publish_ready(path, own, peer, row)

            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["ready.json"])

    def test_peer_run_epoch_node_and_boot_identity_must_match(self):
        own = identity("node-a")
        peer = identity("node-b")
        check_peer(peer, own, "node-b")

        for corruption in ("run", "epoch", "node", "boot"):
            with self.subTest(corruption=corruption):
                bad_peer = copy.deepcopy(peer)
                if corruption == "run":
                    bad_peer["run"] = "other-run"
                elif corruption == "epoch":
                    bad_peer["epoch"] = "other-epoch"
                elif corruption == "node":
                    bad_peer["node"] = "node-a"
                else:
                    bad_peer["boot_id"] = own["boot_id"]
                with self.assertRaises(ValueError):
                    check_peer(bad_peer, own, "node-b")

    def test_ready_verification_requires_successful_cpu_only_preflight_proof(self):
        reference = identity("node-a")
        source = identity("node-b")
        marker = marker_for(reference, source)
        proof = proof_for(reference, source)

        for change in ("status", "classification", "training_claim"):
            with self.subTest(change=change):
                bad_proof = copy.deepcopy(proof)
                if change == "status":
                    bad_proof["status"] = "FAIL"
                elif change == "classification":
                    bad_proof["classification"] = "GPU_CALIBRATED"
                else:
                    bad_proof["training_calibration"] = True
                with patch("tools.g1_04_preflight.verify_live_process"):
                    with self.assertRaises(ValueError):
                        verify_ready(marker, bad_proof, "run-cpu", "epoch-cpu", "node-a", COLLECTOR)

        bad_marker = copy.deepcopy(marker)
        bad_marker["status"] = "UNKNOWN"
        with patch("tools.g1_04_preflight.verify_live_process"):
            with self.assertRaises(ValueError):
                verify_ready(bad_marker, proof, "run-cpu", "epoch-cpu", "node-a", COLLECTOR)

    def test_run_epoch_clock_domain_and_collector_sources_are_bound(self):
        reference = identity("node-a")
        source = identity("node-b")
        marker = marker_for(reference, source)
        server_marker = marker_for(source, reference)
        proof = proof_for(reference, source)

        self.assertEqual(self.verify_cpu_ready(marker, proof, "node-a")["status"], "PASS")
        self.assertEqual(self.verify_cpu_ready(server_marker, proof, "node-b")["status"], "PASS")

        bad_cases = []
        changed_run = copy.deepcopy(marker)
        changed_run["self"]["run"] = "other-run"
        bad_cases.append(("run", changed_run, proof))
        changed_epoch = copy.deepcopy(marker)
        changed_epoch["self"]["epoch"] = "other-epoch"
        bad_cases.append(("epoch", changed_epoch, proof))

        changed_domain = copy.deepcopy(marker)
        changed_domain["peer"]["time_namespace"] = "time:[unrelated]"
        bad_cases.append(("clock_domain", changed_domain, proof))

        changed_digest = copy.deepcopy(proof)
        changed_digest["collector_sha256"] = "0" * 64
        bad_cases.append(("collector_sha256", marker, changed_digest))

        changed_helper = copy.deepcopy(proof)
        changed_helper["host_helper_sha256"] = "f" * 64
        bad_cases.append(("host_helper_sha256", marker, changed_helper))

        for label, bad_marker, bad_proof in bad_cases:
            with self.subTest(mismatch=label):
                with patch("tools.g1_04_preflight.verify_live_process"):
                    with self.assertRaises(ValueError):
                        verify_ready(bad_marker, bad_proof, "run-cpu", "epoch-cpu", "node-a", COLLECTOR)

        with patch("tools.g1_04_preflight.verify_live_process", side_effect=ValueError("process provenance failed")):
            with self.assertRaises(ValueError):
                verify_ready(marker, proof, "run-cpu", "epoch-cpu", "node-a", COLLECTOR)

    def test_new_sidecar_pids_may_differ_from_preflight_pids(self):
        reference = identity("node-a")
        source = identity("node-b")
        proof = proof_for(reference, source)
        # The preflight collectors have exited; the first-exchange sidecars
        # have their own new process identities in the same clock domains.
        new_reference = identity("node-a", pid=os.getpid() + 1001)
        new_source = identity("node-b", pid=os.getpid() + 1002)
        marker = marker_for(new_reference, new_source)
        marker["process_start_ticks"] = 123456

        result = self.verify_cpu_ready(marker, proof, "node-a")
        self.assertEqual(result["status"], "PASS")

    def test_two_node_loopback_publishes_and_verifies_first_exchange_markers(self):
        reference = identity("node-a")
        source = identity("node-b")
        with tempfile.TemporaryDirectory() as directory:
            client_ready = Path(directory) / "client-ready.json"
            server_ready = Path(directory) / "server-ready.json"

            with socket.socket() as reserve:
                reserve.bind(("127.0.0.1", 0))
                port = reserve.getsockname()[1]

            server_result = {}
            server_errors = []

            def serve():
                try:
                    server_result["doc"] = run(
                        "server", "127.0.0.1", port, source, 1, 2, 0.0005, 8,
                        server_ready, "node-a",
                    )
                except Exception as exc:  # surfaced in the parent test thread
                    server_errors.append(exc)

            thread = threading.Thread(target=serve)
            thread.start()
            deadline = time.monotonic() + 5
            client_doc = None
            while client_doc is None:
                try:
                    client_doc = run(
                        "client", "127.0.0.1", port, reference, 1, 2, 0.0005, 8,
                        client_ready, "node-b",
                    )
                except ConnectionRefusedError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.005)

            thread.join(9)
            self.assertFalse(thread.is_alive())
            self.assertEqual(server_errors, [])
            self.assertTrue(client_doc["complete"])
            self.assertTrue(server_result["doc"]["complete"])
            self.assertEqual(client_doc["count"], 2)
            self.assertEqual(server_result["doc"]["count"], 2)

            proof = verify_pair(client_doc, server_result["doc"])
            self.assertEqual(proof["status"], "PASS")
            proof["collector_sha256"] = client_doc["collector_sha256"]
            proof["host_helper_sha256"] = client_doc["host_helper_sha256"]
            client_marker = json.loads(client_ready.read_text())
            server_marker = json.loads(server_ready.read_text())
            self.assertEqual(client_marker["status"], "CONTROL_READY")
            self.assertEqual(server_marker["status"], "CONTROL_READY")
            self.assertEqual(client_marker["first_exchange"]["index"], 0)
            self.assertEqual(server_marker["first_exchange"]["index"], 0)
            self.assertEqual(client_marker["first_exchange"], client_doc["exchanges"][0])
            self.assertEqual(server_marker["first_exchange"], server_result["doc"]["exchanges"][0])
            self.assertEqual(self.verify_cpu_ready(client_marker, proof, "node-a")["status"], "PASS")
            self.assertEqual(self.verify_cpu_ready(server_marker, proof, "node-b")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
