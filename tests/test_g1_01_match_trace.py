import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.g1_01_match_trace import analyze_manifest


FIXTURES = Path(__file__).parent / "fixtures" / "g1_01"


class MatchTraceFixtureTests(unittest.TestCase):
    def _copy_fixtures(self, tempdir: str) -> Path:
        target = Path(tempdir) / "fixture"
        shutil.copytree(FIXTURES, target)
        return target / "manifest.json"

    def _load_trace(self, path: Path) -> list[dict]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_trace(self, path: Path, events: list[dict]) -> None:
        path.write_text(json.dumps(events), encoding="utf-8")

    def _load_manifest(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_manifest(self, path: Path, manifest: dict) -> None:
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_official_async_shape_matches_by_sequence_despite_different_clocks(self) -> None:
        result = analyze_manifest(FIXTURES / "manifest.json")
        self.assertEqual(result["overall_status"], "MATCHED")
        self.assertEqual(result["summary"]["matched"], 2)
        self.assertEqual([row["status"] for row in result["instances"]], ["MATCHED", "MATCHED"])
        self.assertEqual(result["instances"][0]["function"], "AllGather")
        self.assertEqual(result["instances"][1]["count"], 4096)
        self.assertEqual(result["clock_boundaries"][0]["cross_rank_comparable"], False)
        self.assertNotEqual(
            result["clock_boundaries"][0]["first_ts"],
            result["clock_boundaries"][1]["first_ts"],
        )
        self.assertTrue(all(row["dropped"] == "UNKNOWN" for row in result["data_loss"]["ranks"]))
        # OS PIDs can repeat on distinct nodes; the per-node identity is unique.
        self.assertNotIn("42137", json.dumps(result))
        self.assertNotIn("117001", json.dumps(result))

    def test_missing_rank_and_unclosed_begin_remain_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank1.trace.json"
            events = self._load_trace(trace_path)
            # Keep the AllGather begin but remove its end. That event is not
            # guessed from its timestamp and the AllGather peer is missing.
            self._save_trace(trace_path, [event for event in events if not (event.get("cat") == "COLL" and event.get("name") == "AllGather" and event.get("ph") == "e")])
            result = analyze_manifest(manifest_path)
        all_gather = next(row for row in result["instances"] if row["function"] == "AllGather")
        self.assertEqual(all_gather["status"], "MISSING_RANK")
        self.assertEqual(all_gather["missing_global_ranks"], [1])
        self.assertEqual(result["rank_traces"][1]["pairing_issues"], {"ORPHAN_BEGIN": 1})

    def test_duplicate_collective_is_not_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank0.trace.json"
            events = self._load_trace(trace_path)
            pair = [event for event in events if event.get("cat") == "COLL" and event.get("name") == "AllReduce"]
            events.extend(dict(event) for event in pair)
            self._save_trace(trace_path, events)
            result = analyze_manifest(manifest_path)
        all_reduce = next(row for row in result["instances"] if row["function"] == "AllReduce")
        self.assertEqual(all_reduce["status"], "DUPLICATE")
        self.assertEqual(all_reduce["duplicate_global_ranks"], [0])

    def test_orphan_begin_contaminates_a_completed_key(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank0.trace.json"
            events = self._load_trace(trace_path)
            begin = next(event for event in events if event.get("cat") == "COLL" and event.get("name") == "AllReduce" and event.get("ph") == "b")
            orphan = dict(begin)
            orphan["id"] = 999
            orphan["ts"] = max(event.get("ts", 0) for event in events) + 1
            self._save_trace(trace_path, [*events, orphan])
            result = analyze_manifest(manifest_path)
        all_reduce = next(row for row in result["instances"] if row["function"] == "AllReduce")
        all_gather = next(row for row in result["instances"] if row["function"] == "AllGather")
        self.assertEqual(all_reduce["status"], "UNKNOWN")
        self.assertEqual(all_reduce["present_global_ranks"], [0, 1])
        self.assertEqual(all_reduce["pairing_contamination"], [{"global_rank": 0, "reasons": ["ORPHAN_BEGIN"]}])
        self.assertEqual(all_gather["status"], "MATCHED")
        self.assertEqual(result["overall_status"], "PARTIAL")

    def test_repeated_begin_quarantines_token_until_its_end(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank0.trace.json"
            events = self._load_trace(trace_path)
            begin = next(event for event in events if event.get("cat") == "COLL" and event.get("name") == "AllReduce" and event.get("ph") == "b")
            end = next(event for event in events if event.get("cat") == "COLL" and event.get("name") == "AllReduce" and event.get("ph") == "e")
            remaining = [event for event in events if event not in (begin, end)]
            self._save_trace(trace_path, [begin, dict(begin), dict(begin), end, *remaining])
            result = analyze_manifest(manifest_path)
        all_reduce = next(row for row in result["instances"] if row["function"] == "AllReduce")
        self.assertEqual(all_reduce["status"], "MISSING_RANK")
        self.assertEqual(all_reduce["missing_global_ranks"], [0])
        self.assertEqual(result["summary"]["event_pairing_issue_count"], 3)
        self.assertEqual(result["overall_status"], "PARTIAL")

    def test_count_conflict_is_reported_without_forced_match(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank1.trace.json"
            events = self._load_trace(trace_path)
            for event in events:
                if event.get("cat") == "COLL" and event.get("ph") == "b" and event.get("name") == "AllReduce":
                    event["args"]["Count"] = 8192
            self._save_trace(trace_path, events)
            result = analyze_manifest(manifest_path)
        all_reduce = next(row for row in result["instances"] if row["function"] == "AllReduce")
        self.assertEqual(all_reduce["status"], "METADATA_CONFLICT")
        self.assertIn("METADATA_CONFLICT:COUNT", all_reduce["metadata_issues"])

    def test_incomplete_init_inventory_blocks_cross_rank_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            manifest = self._load_manifest(manifest_path)
            manifest["ranks"][0]["comm_inventory_complete"] = False
            self._save_manifest(manifest_path, manifest)
            result = analyze_manifest(manifest_path)
        self.assertEqual(result["overall_status"], "UNKNOWN")
        self.assertIn("COMM_INVENTORY_INCOMPLETE", result["precondition_issues"])
        self.assertTrue(all(row["status"] == "UNKNOWN" for row in result["instances"]))

    def test_bad_comm_hash_and_member_rank_are_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            manifest_path = self._copy_fixtures(tempdir)
            trace_path = manifest_path.parent / "rank1.trace.json"
            events = self._load_trace(trace_path)
            for event in events:
                if event.get("cat") == "COLL" and event.get("ph") == "b" and event.get("name") == "AllReduce":
                    event["args"]["CommHash"] = 999
                if event.get("cat") == "COLL" and event.get("ph") == "b" and event.get("name") == "AllGather":
                    event["args"]["Rank"] = 0
            self._save_trace(trace_path, events)
            result = analyze_manifest(manifest_path)
        self.assertEqual(result["summary"]["comm_hash_mismatch_events"], 1)
        self.assertEqual(result["summary"]["member_mismatch_events"], 1)
        all_reduce = next(row for row in result["instances"] if row["function"] == "AllReduce")
        self.assertEqual(all_reduce["status"], "MISSING_RANK")
        self.assertEqual(all_reduce["missing_global_ranks"], [1])
        self.assertTrue(any(row["reason"] == "COMM_HASH_MISMATCH" for row in result["unkeyed_or_invalid_events"]))
        all_gather = next(row for row in result["instances"] if row["function"] == "AllGather")
        self.assertEqual(all_gather["status"], "MISSING_RANK")
        self.assertTrue(any(row["reason"] == "MEMBER_MISMATCH" for row in result["unkeyed_or_invalid_events"]))


if __name__ == "__main__":
    unittest.main()
