#!/usr/bin/env python3
"""Build the private 4-rank G1-01 manifest from capture records and init logs."""

import argparse
import json
import os
import re
import sys
from pathlib import Path


INIT_RE = re.compile(
    r"PROFILER/Plugin:\s*(init|finalize)\s+commName:\s*(.*?)\s+"
    r"commHash:\s*(\d+)\s+nranks:\s*(\d+)\s+rank:\s*(\d+)"
)
EXPECTED_RANKS = {0, 1, 2, 3}


class BuildError(Exception):
    pass


def integer(value):
    if isinstance(value, bool):
        raise BuildError()
    if isinstance(value, float) and not value.is_integer():
        raise BuildError()
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        raise BuildError() from None


def node_dir(value):
    alias, separator, directory = value.partition("=")
    if not separator or not alias.strip() or not directory.strip():
        raise BuildError()
    return alias.strip(), Path(directory.strip()).expanduser().resolve()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise BuildError() from None


def init_records(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise BuildError() from None
    found = {"init": [], "finalize": []}
    for line in lines:
        match = INIT_RE.search(line)
        if match:
            action, name, comm_hash, nranks, rank = match.groups()
            found[action].append((name, int(comm_hash), int(nranks), int(rank)))
    if len(found["init"]) != 1 or len(found["finalize"]) != 1:
        raise BuildError()
    init, finalize = found["init"][0], found["finalize"][0]
    if not init[0] or init != finalize:
        raise BuildError()
    return init[1:]


def build_manifest(node_dirs):
    if len(node_dirs) != 2 or node_dirs[0][0] == node_dirs[1][0]:
        raise BuildError()
    rank_rows = []
    aliases = {alias for alias, _directory in node_dirs}
    for alias, directory in node_dirs:
        files = sorted(directory.glob("rank-*.json"))
        if len(files) != 2 or any(not re.fullmatch(r"rank-\d+\.json", path.name) for path in files):
            raise BuildError()
        for record_path in files:
            record = read_json(record_path)
            if not isinstance(record, dict):
                raise BuildError()
            rank = integer(record.get("rank"))
            local_rank = integer(record.get("local_rank"))
            pid = integer(record.get("pid"))
            if record.get("node_alias") != alias or record.get("mode") != "multinode":
                raise BuildError()
            if integer(record.get("world_size")) != 4 or rank not in EXPECTED_RANKS or local_rank not in (0, 1) or pid < 1:
                raise BuildError()
            group = record.get("process_group")
            if not isinstance(group, dict) or str(group.get("backend", "")).lower() != "nccl":
                raise BuildError()
            members = group.get("members")
            if not isinstance(members, list):
                raise BuildError()
            members = [integer(member) for member in members]
            if len(members) != 4 or set(members) != EXPECTED_RANKS:
                raise BuildError()

            run_id, epoch = record.get("run_id"), record.get("rank_epoch")
            if not isinstance(run_id, str) or not run_id or not isinstance(epoch, str) or not epoch:
                raise BuildError()
            log_path = directory / f"nccl.{pid}.log"
            comm_hash, nranks, comm_rank = init_records(log_path)
            if nranks != 4 or comm_rank not in EXPECTED_RANKS or members[comm_rank] != rank:
                raise BuildError()
            trace_path = directory / f"trace_{comm_hash}_{comm_rank}.json"
            if not trace_path.is_file():
                raise BuildError()
            rank_rows.append({
                "run_id": run_id, "rank_epoch": epoch, "global_rank": rank,
                "comm_rank": comm_rank, "local_rank": local_rank,
                "node_alias": alias, "pid": pid, "comm_hash": comm_hash,
                "nranks": nranks, "trace_file": str(trace_path), "members": members,
            })

    if len(rank_rows) != 4 or {row["global_rank"] for row in rank_rows} != EXPECTED_RANKS:
        raise BuildError()
    if len({(row["node_alias"], row["pid"]) for row in rank_rows}) != 4:
        raise BuildError()
    if len({(row["node_alias"], row["local_rank"]) for row in rank_rows}) != 4:
        raise BuildError()
    if {row["node_alias"] for row in rank_rows} != aliases:
        raise BuildError()
    if len({row["run_id"] for row in rank_rows}) != 1 or len({row["rank_epoch"] for row in rank_rows}) != 1:
        raise BuildError()
    if len({tuple(row["members"]) for row in rank_rows}) != 1 or len({row["comm_hash"] for row in rank_rows}) != 1:
        raise BuildError()
    if {row["nranks"] for row in rank_rows} != {4} or {row["comm_rank"] for row in rank_rows} != EXPECTED_RANKS:
        raise BuildError()

    by_rank = {row["global_rank"]: row for row in rank_rows}
    members = [
        {"global_rank": by_rank[global_rank]["global_rank"],
         "comm_rank": by_rank[global_rank]["comm_rank"],
         "node_alias": by_rank[global_rank]["node_alias"],
         "local_rank": by_rank[global_rank]["local_rank"]}
        for global_rank in sorted(EXPECTED_RANKS)
    ]
    comm_hash = rank_rows[0]["comm_hash"]
    return {
        "schema_version": 1,
        "run_id": rank_rows[0]["run_id"],
        "rank_epoch": rank_rows[0]["rank_epoch"],
        "comm_inventory_source": "complete_plugin_init_finalize_logs",
        "world_comm": {"comm_hash": comm_hash, "nranks": 4, "members": members},
        "ranks": [
            {"global_rank": row["global_rank"], "comm_rank": row["comm_rank"],
             "node_alias": row["node_alias"], "local_rank": row["local_rank"],
             "pid": row["pid"], "trace_file": row["trace_file"],
             "comm_inventory_complete": True,
             "communicator_inventory": [{"scope": "world", "comm_hash": comm_hash,
                                           "nranks": 4, "comm_rank": row["comm_rank"]}],
             "clock": {"domain": "PROCESS_CLOCK_MONOTONIC_RELATIVE", "unit": "us",
                       "calibration": "UNKNOWN", "uncertainty": "UNKNOWN"},
             "integrity": {"dropped": "UNKNOWN", "truncated": "UNKNOWN"}}
            for row in sorted(rank_rows, key=lambda item: item["global_rank"])
        ],
    }


class QuietParser(argparse.ArgumentParser):
    def error(self, _message):
        self.exit(2, "manifest build failed\n")


def main():
    parser = QuietParser(description=__doc__)
    parser.add_argument("node_dirs", nargs=2, metavar="ALIAS=PRIVATE_DIR")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = build_manifest([node_dir(value) for value in args.node_dirs])
        encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                descriptor = -1
                output.write(encoded)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except Exception:
        print("manifest build failed", file=sys.stderr)
        return 1
    print("manifest written (4 ranks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
