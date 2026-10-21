#!/usr/bin/env python3
"""Conservatively match NCCL profiler example COLL events across ranks.

The manifest carries run/rank identity and a complete per-process communicator
inventory derived from initialization records. This tool never infers world
membership from COLL events and never correlates events by timestamp or pointer.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class InputError(ValueError):
    pass


def _required(obj: dict[str, Any], key: str, context: str) -> Any:
    if key not in obj:
        raise InputError(f"{context}: missing required field {key!r}")
    return obj[key]


def _nonempty_str(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{context}: expected a non-empty string")
    return value.strip()


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise InputError(f"{context}: expected an integer")
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputError(f"{context}: expected an integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise InputError(f"{context}: expected an integer")
    if number < minimum:
        raise InputError(f"{context}: expected a value >= {minimum}")
    return number


def _comm_hash(value: Any, context: str) -> str:
    if isinstance(value, bool) or value is None:
        raise InputError(f"{context}: expected a communicator hash")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            # NCCL example writes an unsigned integer with %lu. Accept hex in
            # user-authored manifests too, while preserving non-numeric IDs.
            return str(int(raw, 0))
        except ValueError:
            return raw
    raise InputError(f"{context}: expected a communicator hash")


@dataclass(frozen=True)
class RankSpec:
    global_rank: int
    comm_rank: int
    node_alias: str
    local_rank: int
    pid: int
    trace_file: Path
    rank_epoch: str
    clock: dict[str, Any]
    integrity: dict[str, Any]
    communicator_inventory: list[dict[str, Any]]
    comm_inventory_complete: bool


@dataclass(frozen=True)
class WorldMember:
    global_rank: int
    comm_rank: int
    node_alias: str
    local_rank: int


@dataclass(frozen=True)
class Collective:
    global_rank: int
    node_alias: str
    local_rank: int
    comm_rank: int
    comm_hash: str | None
    function: str | None
    seq_num: int | None
    count: int | None
    datatype: str | None
    algorithm: str | None
    protocol: str | None
    n_channels: int | None
    metadata_issues: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str, int] | None:
        if self.comm_hash is None or self.function is None or self.seq_num is None:
            return None
        return (self.comm_hash, self.function, self.seq_num)


def _load_json(path: Path) -> Any:
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"could not read JSON input: {path.name}: {exc}") from exc


def _trace_events(payload: Any, trace_name: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        events = payload
    elif isinstance(payload, dict) and isinstance(payload.get("traceEvents"), list):
        events = payload["traceEvents"]
    else:
        raise InputError(f"{trace_name}: expected a JSON array or traceEvents array")
    # The official example may finish its array with an empty-object sentinel.
    return [event for event in events if isinstance(event, dict) and event]


def load_manifest(manifest_path: Path) -> tuple[dict[str, Any], list[RankSpec], dict[str, Any], list[str]]:
    raw = _load_json(manifest_path)
    if not isinstance(raw, dict):
        raise InputError("manifest: expected a JSON object")
    if _required(raw, "schema_version", "manifest") != 1:
        raise InputError("manifest: schema_version must be 1")

    run_id = _nonempty_str(_required(raw, "run_id", "manifest"), "manifest.run_id")
    root_epoch = raw.get("rank_epoch")
    if root_epoch is not None:
        root_epoch = _nonempty_str(root_epoch, "manifest.rank_epoch")

    world = _required(raw, "world_comm", "manifest")
    if not isinstance(world, dict):
        raise InputError("manifest.world_comm: expected an object")
    world_hash = _comm_hash(_required(world, "comm_hash", "manifest.world_comm"), "manifest.world_comm.comm_hash")
    world_size = _integer(_required(world, "nranks", "manifest.world_comm"), "manifest.world_comm.nranks", minimum=1)
    members_raw = _required(world, "members", "manifest.world_comm")
    if not isinstance(members_raw, list):
        raise InputError("manifest.world_comm.members: expected an array")

    members: list[WorldMember] = []
    for index, item in enumerate(members_raw):
        ctx = f"manifest.world_comm.members[{index}]"
        if not isinstance(item, dict):
            raise InputError(f"{ctx}: expected an object")
        members.append(WorldMember(
            global_rank=_integer(_required(item, "global_rank", ctx), f"{ctx}.global_rank"),
            comm_rank=_integer(_required(item, "comm_rank", ctx), f"{ctx}.comm_rank"),
            node_alias=_nonempty_str(_required(item, "node_alias", ctx), f"{ctx}.node_alias"),
            local_rank=_integer(_required(item, "local_rank", ctx), f"{ctx}.local_rank"),
        ))

    ranks_raw = _required(raw, "ranks", "manifest")
    if not isinstance(ranks_raw, list) or not ranks_raw:
        raise InputError("manifest.ranks: expected a non-empty array")

    base_dir = manifest_path.resolve().parent
    ranks: list[RankSpec] = []
    for index, item in enumerate(ranks_raw):
        ctx = f"manifest.ranks[{index}]"
        if not isinstance(item, dict):
            raise InputError(f"{ctx}: expected an object")
        epoch = item.get("rank_epoch", root_epoch)
        if epoch is None:
            raise InputError(f"{ctx}: rank_epoch is required on the rank or manifest")
        epoch = _nonempty_str(epoch, f"{ctx}.rank_epoch")
        trace_file = Path(_nonempty_str(_required(item, "trace_file", ctx), f"{ctx}.trace_file"))
        if not trace_file.is_absolute():
            trace_file = base_dir / trace_file
        inventory = _required(item, "communicator_inventory", ctx)
        if not isinstance(inventory, list) or any(not isinstance(entry, dict) for entry in inventory):
            raise InputError(f"{ctx}.communicator_inventory: expected an array of objects")
        complete = _required(item, "comm_inventory_complete", ctx)
        if not isinstance(complete, bool):
            raise InputError(f"{ctx}.comm_inventory_complete: expected a boolean")
        clock = item.get("clock", {})
        integrity = item.get("integrity", {})
        if not isinstance(clock, dict) or not isinstance(integrity, dict):
            raise InputError(f"{ctx}: clock and integrity must be objects")
        ranks.append(RankSpec(
            global_rank=_integer(_required(item, "global_rank", ctx), f"{ctx}.global_rank"),
            comm_rank=_integer(_required(item, "comm_rank", ctx), f"{ctx}.comm_rank"),
            node_alias=_nonempty_str(_required(item, "node_alias", ctx), f"{ctx}.node_alias"),
            local_rank=_integer(_required(item, "local_rank", ctx), f"{ctx}.local_rank"),
            pid=_integer(_required(item, "pid", ctx), f"{ctx}.pid"),
            trace_file=trace_file,
            rank_epoch=epoch,
            clock=clock,
            integrity=integrity,
            communicator_inventory=inventory,
            comm_inventory_complete=complete,
        ))

    issues: list[str] = []
    global_ranks = [rank.global_rank for rank in ranks]
    if len(global_ranks) != len(set(global_ranks)):
        issues.append("DUPLICATE_GLOBAL_RANK")
    process_ids = [(rank.node_alias, rank.pid) for rank in ranks]
    if len(process_ids) != len(set(process_ids)):
        issues.append("DUPLICATE_NODE_PID")
    node_locals = [(rank.node_alias, rank.local_rank) for rank in ranks]
    if len(node_locals) != len(set(node_locals)):
        issues.append("DUPLICATE_NODE_LOCAL_RANK")
    epochs = {rank.rank_epoch for rank in ranks}
    if len(epochs) != 1:
        issues.append("RANK_EPOCH_MISMATCH")
    if root_epoch is not None and epochs != {root_epoch}:
        issues.append("ROOT_RANK_EPOCH_MISMATCH")

    member_global = [member.global_rank for member in members]
    member_comm = [member.comm_rank for member in members]
    if len(member_global) != len(set(member_global)):
        issues.append("DUPLICATE_MEMBER_GLOBAL_RANK")
    if len(member_comm) != len(set(member_comm)):
        issues.append("DUPLICATE_MEMBER_COMM_RANK")
    if world_size != len(members) or sorted(member_comm) != list(range(world_size)):
        issues.append("INVALID_WORLD_MEMBERSHIP")
    if set(member_global) != set(global_ranks):
        issues.append("MANIFEST_MEMBER_SET_MISMATCH")

    member_by_global = {member.global_rank: member for member in members}
    for rank in ranks:
        member = member_by_global.get(rank.global_rank)
        if member is None:
            continue
        if (member.comm_rank, member.node_alias, member.local_rank) != (
            rank.comm_rank, rank.node_alias, rank.local_rank
        ):
            issues.append("MANIFEST_MEMBER_IDENTITY_MISMATCH")
        world_entries = [entry for entry in rank.communicator_inventory if entry.get("scope") == "world"]
        if not rank.comm_inventory_complete:
            issues.append("COMM_INVENTORY_INCOMPLETE")
        if len(world_entries) != 1:
            issues.append("NON_UNIQUE_WORLD_COMM_PER_PROCESS")
            continue
        entry = world_entries[0]
        try:
            entry_hash = _comm_hash(entry.get("comm_hash"), "communicator_inventory.comm_hash")
            entry_size = _integer(entry.get("nranks"), "communicator_inventory.nranks", minimum=1)
            entry_rank = _integer(entry.get("comm_rank"), "communicator_inventory.comm_rank")
        except InputError:
            issues.append("INVALID_WORLD_COMM_INVENTORY_ENTRY")
            continue
        if (entry_hash, entry_size, entry_rank) != (world_hash, world_size, rank.comm_rank):
            issues.append("WORLD_COMM_INVENTORY_MISMATCH")

    # A row count plus a declared complete inventory is the input evidence that
    # the world mapping came from init records, not from collective matching.
    details = {
        "run_id": run_id,
        "rank_epoch": root_epoch if root_epoch is not None else (next(iter(epochs)) if len(epochs) == 1 else "UNKNOWN"),
        "world_comm_hash": world_hash,
        "world_size": world_size,
        "world_members": members,
    }
    return raw, ranks, details, sorted(set(issues))


def _find_arg(args: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in args:
            return args[name]
    lower = {str(key).lower(): value for key, value in args.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return number


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _normalise_collective(event: dict[str, Any], rank: RankSpec) -> Collective:
    args = event.get("args") if isinstance(event.get("args"), dict) else {}
    name = event.get("name")
    func_arg = _find_arg(args, "func", "Function")
    function = str(func_arg if func_arg is not None else name).strip() if (func_arg is not None or isinstance(name, str)) else None
    issues: list[str] = []
    if not function:
        issues.append("MISSING_FUNCTION")
        function = None
    elif isinstance(name, str) and func_arg is not None and name != str(func_arg):
        issues.append("FUNCTION_NAME_CONFLICT")

    raw_hash = _find_arg(args, "CommHash", "commHash", "comm_hash")
    try:
        comm_hash = _comm_hash(raw_hash, "COLL.args.CommHash") if raw_hash is not None else None
    except InputError:
        comm_hash = None
        issues.append("INVALID_COMM_HASH")
    if comm_hash is None:
        issues.append("MISSING_COMM_HASH")

    comm_rank = _optional_int(_find_arg(args, "Rank", "commRank", "comm_rank"))
    if comm_rank is None:
        issues.append("MISSING_COMM_RANK")
    elif comm_rank != rank.comm_rank:
        issues.append("COMM_RANK_MISMATCH")

    seq_num = _optional_int(_find_arg(args, "SeqNum", "seqNum", "seqNumber", "seq_number"))
    if seq_num is None:
        issues.append("MISSING_SEQ_NUM")
    elif seq_num < 0:
        issues.append("INVALID_SEQ_NUM")
        seq_num = None
    count = _optional_int(_find_arg(args, "Count", "count"))
    if count is not None and count < 0:
        issues.append("INVALID_COUNT")
        count = None
    datatype_value = _find_arg(args, "Datatype", "datatype", "DataType")
    datatype = str(datatype_value) if datatype_value is not None else None
    if count is None:
        issues.append("MISSING_COUNT")
    if datatype is None or not datatype:
        issues.append("MISSING_DATATYPE")
        datatype = None

    return Collective(
        global_rank=rank.global_rank,
        node_alias=rank.node_alias,
        local_rank=rank.local_rank,
        # Preserve the observed communicator rank so a bad member is quarantined
        # instead of being silently attributed to the process's expected rank.
        comm_rank=comm_rank if comm_rank is not None else rank.comm_rank,
        comm_hash=comm_hash,
        function=function,
        seq_num=seq_num,
        count=count,
        datatype=datatype,
        algorithm=(str(_find_arg(args, "Algorithm", "algorithm")) if _find_arg(args, "Algorithm", "algorithm") is not None else None),
        protocol=(str(_find_arg(args, "Protocol", "protocol")) if _find_arg(args, "Protocol", "protocol") is not None else None),
        n_channels=_optional_int(_find_arg(args, "nChannels", "numChannels", "n_channels")),
        metadata_issues=tuple(sorted(set(issues))),
    )


def _event_token(event: dict[str, Any]) -> tuple[str, str, str] | None:
    pid = event.get("pid")
    category = event.get("cat")
    event_id = event.get("id")
    if pid is None or category is None or event_id is None:
        return None
    # The NCCL example emits async events with a process-local ID scoped by
    # category. PID is scoped to the node because OS PIDs may repeat across nodes.
    return (str(pid), str(category), str(event_id))


def _read_rank_trace(rank: RankSpec) -> tuple[list[Collective], dict[str, Any], dict[tuple[str, str, int], set[str]]]:
    payload = _load_json(rank.trace_file)
    events = _trace_events(payload, rank.trace_file.name)
    open_events: dict[tuple[str, str, str], dict[str, Any]] = {}
    ambiguous_tokens: set[tuple[str, str, str]] = set()
    completed: list[Collective] = []
    polluted_keys: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    pair_issues: Counter[str] = Counter()
    bad_pid_events = 0
    coll_event_count = 0
    timestamps: list[float] = []

    for event in events:
        if event.get("cat") != "COLL":
            continue
        phase = event.get("ph")
        if phase not in ("b", "e"):
            continue
        coll_event_count += 1
        try:
            event_pid = int(event.get("pid"))
        except (TypeError, ValueError, OverflowError):
            bad_pid_events += 1
            continue
        if event_pid != rank.pid:
            bad_pid_events += 1
            continue
        ts = _optional_float(event.get("ts"))
        if ts is not None:
            timestamps.append(ts)

        token = _event_token(event)
        if token is None:
            pair_issues["MISSING_PAIR_ID"] += 1
            if phase == "b":
                collective = _normalise_collective(event, rank)
                if collective.key is not None:
                    polluted_keys[collective.key].add("MISSING_PAIR_ID")
            continue
        if phase == "b":
            if token in ambiguous_tokens:
                pair_issues["AMBIGUOUS_BEGIN"] += 1
                collective = _normalise_collective(event, rank)
                if collective.key is not None:
                    polluted_keys[collective.key].add("AMBIGUOUS_BEGIN")
                continue
            if token in open_events:
                pair_issues["DUPLICATE_BEGIN"] += 1
                previous = open_events.pop(token)
                for candidate in (previous, event):
                    collective = _normalise_collective(candidate, rank)
                    if collective.key is not None:
                        polluted_keys[collective.key].add("DUPLICATE_BEGIN")
                ambiguous_tokens.add(token)
                continue
            open_events[token] = event
            continue

        if token in ambiguous_tokens:
            pair_issues["AMBIGUOUS_END"] += 1
            ambiguous_tokens.remove(token)
            continue

        begin = open_events.pop(token, None)
        if begin is None:
            pair_issues["ORPHAN_END"] += 1
            continue
        collective = _normalise_collective(begin, rank)
        completed.append(collective)

    for event in open_events.values():
        pair_issues["ORPHAN_BEGIN"] += 1
        collective = _normalise_collective(event, rank)
        if collective.key is not None:
            polluted_keys[collective.key].add("ORPHAN_BEGIN")
    for _token in ambiguous_tokens:
        pair_issues["AMBIGUOUS_OPEN_AT_EOF"] += 1

    boundary = {
        "first_ts": min(timestamps) if timestamps else None,
        "last_ts": max(timestamps) if timestamps else None,
        "clock_domain": rank.clock.get("domain", "UNKNOWN"),
        "unit": rank.clock.get("unit", "UNKNOWN"),
        "calibration": rank.clock.get("calibration", "UNKNOWN"),
        "uncertainty": rank.clock.get("uncertainty", "UNKNOWN"),
        "cross_rank_comparable": False,
    }
    info = {
        "coll_phase_events": coll_event_count,
        "paired_collectives": len(completed),
        "bad_pid_events": bad_pid_events,
        "pairing_issues": dict(sorted(pair_issues.items())),
        "trace_boundary": boundary,
        "dropped": rank.integrity.get("dropped", "UNKNOWN"),
        "truncated": rank.integrity.get("truncated", "UNKNOWN"),
    }
    return completed, info, polluted_keys


def _rank_label(rank: RankSpec, redact: bool) -> str:
    return f"rank-{rank.global_rank}" if redact else f"{rank.node_alias}/g{rank.global_rank}/l{rank.local_rank}"


def analyze_manifest(manifest_path: Path, *, redact_identifiers: bool = False) -> dict[str, Any]:
    raw_manifest, rank_specs, details, precondition_issues = load_manifest(manifest_path)
    world_hash = details["world_comm_hash"]
    world_size = details["world_size"]
    members: list[WorldMember] = details["world_members"]
    member_by_comm_rank = {member.comm_rank: member for member in members}

    traces: dict[int, list[Collective]] = {}
    polluted_by_key: dict[tuple[str, str, int], dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    rank_reports: list[dict[str, Any]] = []
    for rank in sorted(rank_specs, key=lambda item: (item.global_rank, item.node_alias, item.local_rank)):
        collectives, trace_info, polluted_keys = _read_rank_trace(rank)
        traces[rank.global_rank] = collectives
        for key, reasons in polluted_keys.items():
            polluted_by_key[key][rank.global_rank].update(reasons)
        rank_reports.append({
            "rank": _rank_label(rank, redact_identifiers),
            "global_rank": rank.global_rank,
            "comm_rank": rank.comm_rank,
            "node_alias": "REDACTED" if redact_identifiers else rank.node_alias,
            "local_rank": rank.local_rank,
            **trace_info,
        })

    all_by_key: dict[tuple[str, str, int], dict[int, list[Collective]]] = defaultdict(lambda: defaultdict(list))
    unknown_events: list[dict[str, Any]] = []
    comm_mismatch_count = 0
    member_mismatch_count = 0
    for rank in rank_specs:
        for event in traces[rank.global_rank]:
            if event.comm_hash is not None and event.comm_hash != world_hash:
                comm_mismatch_count += 1
                unknown_events.append({"rank": _rank_label(rank, redact_identifiers), "reason": "COMM_HASH_MISMATCH"})
                continue
            member = member_by_comm_rank.get(event.comm_rank)
            if event.comm_rank < 0 or member is None or member.global_rank != rank.global_rank:
                member_mismatch_count += 1
                unknown_events.append({"rank": _rank_label(rank, redact_identifiers), "reason": "MEMBER_MISMATCH"})
                continue
            if event.key is None:
                unknown_events.append({"rank": _rank_label(rank, redact_identifiers), "reason": "MISSING_COLLECTIVE_KEY"})
                continue
            all_by_key[event.key][rank.global_rank].append(event)

    instances: list[dict[str, Any]] = []
    expected_global_ranks = sorted(member.global_rank for member in members)
    can_match = not precondition_issues
    all_keys = set(all_by_key) | set(polluted_by_key)
    for comm_hash, function, seq_num in sorted(all_keys, key=lambda key: (key[1], key[2])):
        by_rank = all_by_key.get((comm_hash, function, seq_num), {})
        polluted = polluted_by_key.get((comm_hash, function, seq_num), {})
        present = sorted(by_rank)
        missing = sorted(set(expected_global_ranks) - set(present))
        duplicates = sorted(global_rank for global_rank, events in by_rank.items() if len(events) > 1)
        conflicts: set[str] = set()
        for global_rank, events in by_rank.items():
            if len(events) > 1:
                continue
            conflicts.update(events[0].metadata_issues)
        unique_events = [events[0] for events in by_rank.values() if len(events) == 1]
        for field_name in ("count", "datatype", "algorithm", "protocol", "n_channels"):
            values = {getattr(event, field_name) for event in unique_events if getattr(event, field_name) is not None}
            missing_values = any(getattr(event, field_name) is None for event in unique_events)
            if len(values) > 1:
                conflicts.add(f"METADATA_CONFLICT:{field_name.upper()}")
            elif missing_values:
                conflicts.add(f"METADATA_UNKNOWN:{field_name.upper()}")

        if precondition_issues:
            status = "UNKNOWN"
        elif duplicates:
            status = "DUPLICATE"
        elif any(item.startswith("METADATA_CONFLICT") or item in {
            "COMM_RANK_MISMATCH", "COMM_HASH_MISMATCH", "FUNCTION_NAME_CONFLICT"
        } for item in conflicts):
            status = "METADATA_CONFLICT"
        elif missing:
            status = "MISSING_RANK"
        elif polluted:
            status = "UNKNOWN"
        elif conflicts:
            status = "UNKNOWN"
        else:
            status = "MATCHED"

        output = {
            "function": function,
            "seq_num": seq_num,
            "status": status,
            "present_global_ranks": present,
            "missing_global_ranks": missing,
            "duplicate_global_ranks": duplicates,
            "metadata_issues": sorted(conflicts),
            "pairing_contamination": [
                {"global_rank": global_rank, "reasons": sorted(reasons)}
                for global_rank, reasons in sorted(polluted.items())
            ],
        }
        if len(unique_events) == len(by_rank) and unique_events:
            for output_name, field_name in (("count", "count"), ("datatype", "datatype"),
                                            ("algorithm", "algorithm"), ("protocol", "protocol"),
                                            ("n_channels", "n_channels")):
                values = {getattr(event, field_name) for event in unique_events}
                output[output_name] = next(iter(values)) if len(values) == 1 else "UNKNOWN"
        instances.append(output)

    status_counts = Counter(instance["status"] for instance in instances)
    pairing_issue_count = sum(sum(rank["pairing_issues"].values()) for rank in rank_reports)
    bad_pid_event_count = sum(rank["bad_pid_events"] for rank in rank_reports)
    if precondition_issues:
        overall = "UNKNOWN"
    elif status_counts["METADATA_CONFLICT"] or status_counts["DUPLICATE"]:
        overall = "PARTIAL"
    elif status_counts["MISSING_RANK"] or status_counts["UNKNOWN"] or unknown_events or pairing_issue_count or bad_pid_event_count:
        overall = "PARTIAL"
    elif instances:
        overall = "MATCHED"
    else:
        overall = "UNKNOWN"

    output: dict[str, Any] = {
        "schema_version": 1,
        "classification": "CPU_FIXTURE_OR_TRACE_PARSER_ONLY",
        "run_id": "REDACTED" if redact_identifiers else details["run_id"],
        "rank_epoch": "REDACTED" if redact_identifiers else details["rank_epoch"],
        "overall_status": overall,
        "matching_scope": "run_id + rank_epoch + verified_world_comm + func + seq_num",
        "time_matching": "NOT_USED",
        "cross_rank_clock_comparison": "NOT_PERFORMED",
        "precondition_issues": precondition_issues,
        "summary": {
            "expected_ranks": world_size,
            "parsed_rank_traces": len(rank_reports),
            "collective_keys": len(instances),
            "matched": status_counts["MATCHED"],
            "missing_rank": status_counts["MISSING_RANK"],
            "duplicates": status_counts["DUPLICATE"],
            "metadata_conflicts": status_counts["METADATA_CONFLICT"],
            "unknown": status_counts["UNKNOWN"] + len(unknown_events) + pairing_issue_count + bad_pid_event_count,
            "comm_hash_mismatch_events": comm_mismatch_count,
            "member_mismatch_events": member_mismatch_count,
            "event_pairing_issue_count": pairing_issue_count,
            "bad_pid_event_count": bad_pid_event_count,
        },
        "rank_traces": rank_reports,
        "instances": instances,
        "unkeyed_or_invalid_events": unknown_events,
        "data_loss": {
            "meaning": "per-rank manifest declaration; absence remains UNKNOWN",
            "ranks": [
                {"rank": report["rank"], "dropped": report["dropped"], "truncated": report["truncated"]}
                for report in rank_reports
            ],
        },
        "clock_boundaries": [
            {"rank": report["rank"], **report["trace_boundary"]} for report in rank_reports
        ],
    }
    if not can_match:
        output["matching_scope_status"] = "UNKNOWN_DUE_TO_MANIFEST_PRECONDITIONS"
    else:
        output["matching_scope_status"] = "MANIFEST_CONSISTENT"
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest with rank identities and init-derived world comm mapping")
    parser.add_argument("-o", "--output", type=Path, help="write JSON summary to this path (default: stdout)")
    parser.add_argument("--redact-identifiers", action="store_true", help="replace run/rank/node labels in the summary")
    args = parser.parse_args(argv)
    try:
        result = analyze_manifest(args.manifest, redact_identifiers=args.redact_identifiers)
    except InputError as exc:
        print(f"g1_01_match_trace: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
