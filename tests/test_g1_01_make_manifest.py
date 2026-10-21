"""Synthetic CPU-only builder fixture; it is not GPU or MULTINODE evidence."""

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.g1_01_match_trace import analyze_manifest


REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "tools" / "g1_01_make_manifest.py"
COMM_HASH = 184467


class ManifestBuilderSyntheticTests(unittest.TestCase):
    def test_builds_four_rank_manifest_from_records_and_full_init_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node_dirs = [root / "node-a-private", root / "node-b-private"]
            for directory in node_dirs:
                directory.mkdir()

            for global_rank in range(4):
                node_index = global_rank // 2
                node_alias = f"node-{('a', 'b')[node_index]}"
                directory = node_dirs[node_index]
                local_rank = global_rank % 2
                # Synthetic PIDs intentionally repeat across nodes.
                pid = 7100 + local_rank
                record = {
                    "run_id": "synthetic-run",
                    "rank_epoch": "synthetic-epoch",
                    "node_alias": node_alias,
                    "mode": "multinode",
                    "rank": global_rank,
                    "local_rank": local_rank,
                    "world_size": 4,
                    "pid": pid,
                    "process_group": {"backend": "nccl", "members": [0, 1, 2, 3]},
                }
                (directory / f"rank-{global_rank}.json").write_text(json.dumps(record), encoding="utf-8")
                init = (
                    f"[synthetic] NCCL INFO PROFILER/Plugin: init commName: world-0 "
                    f"commHash: {COMM_HASH} nranks: 4 rank: {global_rank}\n"
                )
                finalize = (
                    f"[synthetic] NCCL INFO PROFILER/Plugin: finalize commName: world-0 "
                    f"commHash: {COMM_HASH} nranks: 4 rank: {global_rank}\n"
                )
                (directory / f"nccl.{pid}.log").write_text(init + finalize, encoding="utf-8")
                (directory / f"trace_{COMM_HASH}_{global_rank}.json").write_text("[]\n", encoding="utf-8")

            output = root / "private-manifest.json"
            command = [
                sys.executable, str(BUILDER),
                f"node-a={node_dirs[0]}", f"node-b={node_dirs[1]}",
                "--output", str(output),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout, "manifest written (4 ranks)\n")
            self.assertNotIn(str(root), completed.stdout + completed.stderr)
            self.assertNotIn(str(pid), completed.stdout + completed.stderr)
            self.assertNotIn(str(COMM_HASH), completed.stdout + completed.stderr)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], "synthetic-run")
            self.assertEqual(manifest["rank_epoch"], "synthetic-epoch")
            self.assertEqual(manifest["world_comm"]["comm_hash"], COMM_HASH)
            self.assertEqual([rank["global_rank"] for rank in manifest["ranks"]], [0, 1, 2, 3])
            self.assertEqual([rank["comm_rank"] for rank in manifest["ranks"]], [0, 1, 2, 3])
            self.assertEqual(
                [rank["clock"]["domain"] for rank in manifest["ranks"]],
                ["PROCESS_CLOCK_MONOTONIC_RELATIVE"] * 4,
            )
            self.assertTrue(all(rank["integrity"]["dropped"] == "UNKNOWN" for rank in manifest["ranks"]))
            self.assertTrue(all(Path(rank["trace_file"]).is_absolute() for rank in manifest["ranks"]))
            parsed = analyze_manifest(output)
            self.assertEqual(parsed["matching_scope_status"], "MANIFEST_CONSISTENT")
            self.assertEqual(parsed["summary"]["expected_ranks"], 4)
            self.assertEqual(parsed["overall_status"], "UNKNOWN")  # Empty synthetic traces contain no collectives.


if __name__ == "__main__":
    unittest.main()
