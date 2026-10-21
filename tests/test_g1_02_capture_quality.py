import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.g1_02_capture_quality import analyze_manifest


FIXTURES = Path(__file__).parent / "fixtures" / "g1_01"


class CaptureQualityFixtureTests(unittest.TestCase):
    def test_reversed_and_unknown_local_pair_times_remain_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._copy_fixtures(directory)
            trace = manifest.parent / "rank0.trace.json"
            events = self._load_trace(trace)
            reversed_pair = self._collective_pair(42137, 0, 8, 90, 500)
            reversed_pair[1]["ts"] = 499
            unknown_pair = self._collective_pair(42137, 0, 9, 91, 510)
            unknown_pair[1].pop("ts")
            events += reversed_pair + unknown_pair
            self._save_trace(trace, events)
            rank = analyze_manifest(manifest)["ranks"][0]
            issues = rank["event_classes"]["Coll"]["pairing_issues"]
            self.assertEqual(issues["REVERSED_LOCAL_PAIR_TIME"], 1)
            self.assertEqual(issues["UNKNOWN_LOCAL_PAIR_TIME"], 1)

    def test_cli_and_integrated_clock_quality(self):
        result = subprocess.run([sys.executable, "tools/g1_02_capture_quality.py", str(FIXTURES / "manifest.json")],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema_name"], "CaptureQuality")
        for rank in data["ranks"]:
            for clock in rank["clocks"].values():
                self.assertEqual(clock["status"], "UNSAFE")
                self.assertEqual(clock["uncertainty"], "UNKNOWN")
                self.assertFalse(clock["usable_for_cross_rank"])

    def test_foreign_or_missing_identity_is_quarantined(self):
        for key, value in (("CommHash", 999), ("CommHash", None), ("Rank", None), ("Rank", 1)):
            with self.subTest(key=key, value=value), tempfile.TemporaryDirectory() as directory:
                manifest = self._copy_fixtures(directory)
                trace = manifest.parent / "rank0.trace.json"
                events = self._load_trace(trace)
                extra = self._collective_pair(42137, 0, 500, 90, 500)
                if value is None:
                    extra[0]["args"].pop(key)
                else:
                    extra[0]["args"][key] = value
                events.extend(extra)
                self._save_trace(trace, events)
                rank = analyze_manifest(manifest)["ranks"][0]
                self.assertEqual(rank["quarantined_collective_begin_count"], 1)
                op = next(x for x in rank["operations"] if x["operation"] == "AllReduce")
                self.assertEqual(op["seq_max"], 7)
                self.assertEqual(op["paired_count"], 1)

    def test_invalid_pid_and_missing_sequence_cannot_look_continuous(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._copy_fixtures(directory)
            trace = manifest.parent / "rank0.trace.json"
            events = self._load_trace(trace)
            events.extend(self._collective_pair(42137.5, 0, 500, 90, 500))
            events.extend(self._collective_pair(True, 0, 501, 91, 501))
            extra = self._collective_pair(42137, 0, 502, 92, 502)
            extra[0]["args"].pop("SeqNum")
            events.extend(extra)
            self._save_trace(trace, events)
            rank = analyze_manifest(manifest)["ranks"][0]
            self.assertEqual(rank["bad_pid_event_count"], 4)
            op = next(x for x in rank["operations"] if x["operation"] == "AllReduce")
            self.assertEqual(op["seq_max"], 7)
            self.assertEqual(op["unknown_sequence_begin_count"], 1)
            self.assertEqual(op["sequence_status"], "UNKNOWN")

    def test_contiguous_export_does_not_observe_shared_head_tail_omission(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._copy_fixtures(directory)
            for rank in range(2):
                trace = manifest.parent / f"rank{rank}.trace.json"
                # Identical exported data could originate from a longer history
                # with omitted head/tail; no input evidence distinguishes it.
                events = self._collective_pair(42137, rank, 7, 0, 100)
                events += self._collective_pair(42137, rank, 8, 1, 102)
                self._save_trace(trace, events)
            data = analyze_manifest(manifest)
            self.assertEqual(data["interpretation"]["common_sequence_omissions"], "UNKNOWN")
            for rank in data["ranks"]:
                self.assertEqual(rank["operations"][0]["missing_exported_sequence_slot_count"], 0)
                self.assertEqual(rank["operations"][0]["sequence_completeness_status"], "UNKNOWN")
                self.assertEqual(rank["telemetry"]["dropped"], "UNKNOWN")

    def _copy_fixtures(self, tempdir: str) -> Path:
        target = Path(tempdir) / "fixture"
        shutil.copytree(FIXTURES, target)
        return target / "manifest.json"

    def _load_trace(self, path: Path) -> list[dict]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_trace(self, path: Path, events: list[dict]) -> None:
        path.write_text(json.dumps(events), encoding="utf-8")

    @staticmethod
    def _collective_pair(pid: int, rank: int, seq: int, event_id: int, ts: float) -> list[dict]:
        return [
            {
                "name": "AllReduce",
                "cat": "COLL",
                "ph": "b",
                "id": event_id,
                "pid": pid,
                "tid": 1,
                "ts": ts,
                "args": {
                    "SeqNum": seq,
                    "CommHash": 117001,
                    "Rank": rank,
                    "Count": 4096,
                    "Datatype": "float32",
                },
            },
            {"name": "AllReduce", "cat": "COLL", "ph": "e", "id": event_id, "pid": pid, "tid": 1, "ts": ts + 1},
        ]

    @staticmethod
    def _async_pair(name: str, category: str, pid: int, event_id: int, ts: float) -> list[dict]:
        return [
            {"name": name, "cat": category, "ph": "b", "id": event_id, "pid": pid, "tid": 1, "ts": ts},
            {"name": name, "cat": category, "ph": "e", "id": event_id, "pid": pid, "tid": 1, "ts": ts + 1},
        ]

    def test_report_redacts_identity_and_keeps_unsupported_claims_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["ranks"][0]["integrity"]["dropped"] = 0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            result = analyze_manifest(manifest_path)

        encoded = json.dumps(result)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["world"]["communicator_alias"], "world")
        self.assertEqual(result["world"]["membership_status"], "VERIFIED")
        self.assertEqual(result["run_id"], "REDACTED")
        self.assertEqual(result["rank_epoch"], "REDACTED")
        self.assertNotIn("42137", encoded)
        self.assertNotIn("117001", encoded)
        self.assertNotIn("fixture-run-a", encoded)
        self.assertNotIn("epoch-0", encoded)
        self.assertNotIn("rank0.trace.json", encoded)

        rank0 = result["ranks"][0]
        self.assertEqual(rank0["trace_input"]["parse_status"], "OBSERVED_SUCCESS")
        self.assertRegex(rank0["trace_input"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(rank0["trace_input"]["producer_flush_status"], "UNKNOWN")
        self.assertEqual(rank0["telemetry"]["dropped"], "UNKNOWN")
        self.assertEqual(rank0["event_classes"]["Coll"]["paired_count"], 2)
        self.assertEqual(rank0["event_classes"]["KernelCh"]["paired_count"], 1)
        self.assertEqual(rank0["event_classes"]["Proxy"]["observed_begin_count"], 0)
        self.assertEqual(result["interpretation"]["unobserved_operations"], "UNKNOWN")
        self.assertEqual(result["interpretation"]["head_coverage"], "UNKNOWN")
        self.assertEqual(result["interpretation"]["tail_coverage"], "UNKNOWN")

    def test_gaps_duplicates_and_common_omission_stay_conservative(self) -> None:
        huge_seq = 10**12
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            for rank, pid in enumerate((42137, 42137)):
                trace_path = manifest_path.parent / f"rank{rank}.trace.json"
                events = self._load_trace(trace_path)
                events.extend(self._collective_pair(pid, rank, huge_seq, 20, 200.0))
                events.extend(self._collective_pair(pid, rank, huge_seq, 21, 202.0))
                self._save_trace(trace_path, events)
            result = analyze_manifest(manifest_path)

        for rank_report in result["ranks"]:
            all_reduce = next(op for op in rank_report["operations"] if op["operation"] == "AllReduce")
            self.assertEqual(all_reduce["observed_begin_count"], 3)
            self.assertEqual(all_reduce["paired_count"], 3)
            self.assertEqual(all_reduce["seq_min"], 7)
            self.assertEqual(all_reduce["seq_max"], huge_seq)
            self.assertEqual(all_reduce["duplicate_seq_count"], 1)
            self.assertEqual(all_reduce["internal_seq_gap_ranges"], [{"start": 8, "end": huge_seq - 1}])
            self.assertEqual(all_reduce["missing_exported_sequence_slot_count"], huge_seq - 8)
            self.assertEqual(
                all_reduce["gap_interpretation"],
                "MISSING_EXPORTED_SEQUENCE_SLOTS; NOT_PROVEN_COLLECTOR_DROPS",
            )
        self.assertEqual(result["interpretation"]["common_sequence_omissions"], "UNKNOWN")
        self.assertTrue(result["interpretation"]["same_gap_on_all_ranks_does_not_prove_common_collector_loss"])

    def test_event_classes_pair_separately_and_report_export_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank0.trace.json"
            events = self._load_trace(trace_path)
            events.extend(self._async_pair("Group", "GROUP", 42137, 30, 300.0))
            events.extend(self._async_pair("ProxyStep", "PROXY", 42137, 31, 310.0))
            events.append({"name": "ProxyStep", "cat": "PROXY", "ph": "b", "id": 32, "pid": 42137, "tid": 1, "ts": 320.0})
            events.append({"name": "ProxyStep", "cat": "PROXY", "ph": "e", "id": 33, "pid": 42137, "tid": 1, "ts": 330.0})
            self._save_trace(trace_path, events)
            result = analyze_manifest(manifest_path)

        rank0 = result["ranks"][0]
        self.assertEqual(rank0["event_classes"]["Coll"]["paired_count"], 2)
        self.assertEqual(rank0["event_classes"]["KernelCh"]["paired_count"], 1)
        self.assertEqual(rank0["event_classes"]["Group"]["paired_count"], 1)
        self.assertEqual(rank0["event_classes"]["Proxy"]["paired_count"], 1)
        self.assertEqual(rank0["event_classes"]["Proxy"]["pairing_issues"], {"ORPHAN_BEGIN": 1, "ORPHAN_END": 1})
        self.assertEqual(rank0["exported_window"]["first_ts"], 100.0)
        self.assertEqual(rank0["exported_window"]["last_ts"], 330.0)
        self.assertEqual(rank0["exported_window"]["minimum_ts"], 100.0)
        self.assertEqual(rank0["exported_window"]["maximum_ts"], 330.0)
        self.assertEqual(rank0["collector_active_window"], "UNKNOWN")

    def test_missing_and_truncated_trace_inputs_are_unknown_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            (manifest_path.parent / "rank1.trace.json").unlink()
            (manifest_path.parent / "rank0.trace.json").write_text('[{"name":"AllReduce"}', encoding="utf-8")
            result = analyze_manifest(manifest_path)

        rank0, rank1 = result["ranks"]
        self.assertEqual(rank0["trace_input"]["parse_status"], "UNKNOWN")
        self.assertEqual(rank0["trace_input"]["export_failure"], {
            "status": "UNKNOWN", "source": "trace_file", "reason": "TRACE_PARSE_FAILED_OR_TRUNCATED"
        })
        self.assertRegex(rank0["trace_input"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(rank1["trace_input"]["parse_status"], "UNKNOWN")
        self.assertEqual(rank1["trace_input"]["sha256"], "UNKNOWN")
        self.assertEqual(rank1["trace_input"]["export_failure"]["source"], "trace_file")
        self.assertEqual(rank1["event_classes"]["Coll"]["paired_count"], "UNKNOWN")
        self.assertEqual(result["summary"]["all_capture_counters"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
