"""CPU-only validation for the two-node TCP control preflight, not training coverage."""
import copy
import unittest

from tests.test_g1_04_causal import captures
from tools.g1_04_preflight import validate_config, verify_pair


def control_pair():
    client, server = captures()
    client["reference"].update(node="node-a", boot_id="boot-node-a")
    client["source"].update(node="node-b", boot_id="boot-node-b")
    server["reference"] = copy.deepcopy(client["reference"])
    server["source"] = copy.deepcopy(client["source"])
    return client, server


class G104PreflightTests(unittest.TestCase):
    def assert_pair_fails(self, client, server):
        result = verify_pair(client, server)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["reasons"])

    def test_literal_distinct_ipv4_addresses_and_expected_roles_are_required(self):
        validate_config("192.0.2.10", "192.0.2.11")

        invalid_addresses = (
            ("192.0.2.10", "192.0.2.10"),
            ("localhost", "192.0.2.11"),
            ("192.0.2.10", "example.invalid"),
            ("::1", "192.0.2.11"),
        )
        for ddp, control in invalid_addresses:
            with self.subTest(ddp=ddp, control=control):
                with self.assertRaises(ValueError):
                    validate_config(ddp, control)

        for reference, source in (("node-a", "node-a"), ("node-b", "node-a")):
            with self.subTest(reference=reference, source=source):
                with self.assertRaises(ValueError):
                    validate_config("192.0.2.10", "192.0.2.11", reference, source)

    def test_valid_complete_pair_passes_without_audits(self):
        client, server = control_pair()

        result = verify_pair(client, server)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["reasons"], [])

    def test_missing_rows_count_mismatch_and_bad_index_fail(self):
        for corruption in ("missing_row", "count", "index"):
            with self.subTest(corruption=corruption):
                client, server = control_pair()
                if corruption == "missing_row":
                    server["exchanges"].pop()
                    server["count"] -= 1
                elif corruption == "count":
                    client["count"] -= 1
                else:
                    client["exchanges"][1]["index"] = 9
                    server["exchanges"][1]["index"] = 9
                self.assert_pair_fails(client, server)

    def test_client_and_server_must_report_the_same_complete_schema(self):
        for doc_name, field, value in (
            ("client", "schema", "unknown"),
            ("server", "classification", "CPU_SYNTHETIC"),
            ("client", "transport", "TRAINING_COMMUNICATOR"),
            ("server", "phase", "pre"),
            ("client", "unit", "us"),
        ):
            with self.subTest(doc=doc_name, field=field):
                client, server = control_pair()
                (client if doc_name == "client" else server)[field] = value
                self.assert_pair_fails(client, server)

        for doc_name in ("client", "server"):
            with self.subTest(incomplete=doc_name):
                client, server = control_pair()
                (client if doc_name == "client" else server)["complete"] = False
                self.assert_pair_fails(client, server)

    def test_reference_and_source_roles_must_be_distinct_and_ordered(self):
        client, server = control_pair()
        client["source"] = copy.deepcopy(client["reference"])
        server["source"] = copy.deepcopy(client["source"])
        self.assert_pair_fails(client, server)

        client, server = control_pair()
        client["reference"], client["source"] = client["source"], client["reference"]
        server["source"] = copy.deepcopy(client["source"])
        self.assert_pair_fails(client, server)

    def test_run_epoch_boot_and_exact_source_identity_must_agree(self):
        for corruption in ("run", "epoch", "boot", "source_pid"):
            with self.subTest(corruption=corruption):
                client, server = control_pair()
                if corruption == "run":
                    client["source"]["run"] = "other-run"
                    server["source"] = copy.deepcopy(client["source"])
                elif corruption == "epoch":
                    client["source"]["epoch"] = "other-epoch"
                    server["source"] = copy.deepcopy(client["source"])
                elif corruption == "boot":
                    client["source"]["boot_id"] = client["reference"]["boot_id"]
                    server["source"] = copy.deepcopy(client["source"])
                else:
                    server["source"]["pid"] += 1
                self.assert_pair_fails(client, server)

        client, server = control_pair()
        server.pop("reference")
        self.assert_pair_fails(client, server)

    def test_each_server_timestamp_triplet_must_match_client_and_be_monotonic(self):
        client, server = control_pair()
        server["exchanges"][1]["t1"] += 1
        self.assert_pair_fails(client, server)

        for clock in ("reference", "source"):
            with self.subTest(clock=clock):
                client, server = control_pair()
                if clock == "reference":
                    # t1 is shared by both files; preserve row agreement while
                    # forcing a reference-clock rollback.
                    client["exchanges"][1]["t1"] = 90_000
                    server["exchanges"][1]["t1"] = 90_000
                else:
                    # Source receive/send stamps roll back behind exchange 0.
                    client["exchanges"][1].update(t2=190_000, t3=195_000)
                    server["exchanges"][1].update(t2=190_000, t3=195_000)
                self.assert_pair_fails(client, server)


if __name__ == "__main__":
    unittest.main()
