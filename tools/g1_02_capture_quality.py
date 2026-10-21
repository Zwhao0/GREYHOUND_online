#!/usr/bin/env python3
"""Summarize exported NCCL profiler trace quality without inferring collector loss.

This is a CPU-only, offline report. Sequence gaps describe missing exported
sequence slots; they do not establish that the collector dropped those events.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.g1_01_match_trace import (
        InputError,
        RankSpec,
        _event_token,
        _load_json,
        _normalise_collective,
        _optional_float,
        _optional_int,
        _trace_events,
        load_manifest,
    )
except ModuleNotFoundError as exc:
    # Running ``python tools/g1_02_capture_quality.py`` puts tools/ at sys.path[0].
    if exc.name != "tools":
        raise
    from g1_01_match_trace import (  # type: ignore[no-redef]
        InputError,
        RankSpec,
        _event_token,
        _load_json,
        _normalise_collective,
        _optional_float,
        _optional_int,
        _trace_events,
        load_manifest,
    )

try:
    from tools.g1_02_clock_quality import assess_clock_quality
except ModuleNotFoundError as exc:
    if exc.name != "tools":
        raise
    from g1_02_clock_quality import assess_clock_quality


EVENT_CLASSES = ("Coll", "KernelCh", "Proxy", "Group")
_PROXY_NAMES = {"proxyop", "proxystep"}


def _event_class(event: dict[str, Any]) -> str | None:
    category = str(event.get("cat", "")).strip().casefold()
    name = str(event.get("name", "")).strip().casefold()
    if category == "coll":
        return "Coll"
    if name == "kernelch":
        return "KernelCh"
    if name in _PROXY_NAMES or category in {"proxy", "proxyop", "proxystep"}:
        return "Proxy"
    if name == "group" or category == "group":
        return "Group"
    return None


def _sha256(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def _class_stats() -> dict[str, dict[str, Any]]:
    return {
        event_class: {
            "observed_begin_count": 0,
            "observed_end_count": 0,
            "attributed_begin_count": 0,
            "paired_count": 0,
            "pairing_issues": Counter(),
        }
        for event_class in EVENT_CLASSES
    }


def _operation_stats() -> dict[str, dict[str, Any]]:
    return {
        "observed_begin_count": 0,
        "paired_count": 0,
        "sequence_values": Counter(),
        "pairing_issues": Counter(),
        "parser_issues": Counter(),
    }


def _read_events(rank: RankSpec) -> tuple[str | None, list[dict[str, Any]] | None, dict[str, str] | None]:
    digest = _sha256(rank.trace_file)
    if digest is None:
        reason = "TRACE_FILE_MISSING" if not rank.trace_file.exists() else "TRACE_FILE_UNREADABLE"
        return None, None, {"status": "UNKNOWN", "source": "trace_file", "reason": reason}
    try:
        payload = _load_json(rank.trace_file)
        events = _trace_events(payload, "trace input")
    except InputError:
        return digest, None, {
            "status": "UNKNOWN",
            "source": "trace_file",
            "reason": "TRACE_PARSE_FAILED_OR_TRUNCATED",
        }
    return digest, events, None


def _seq_summary(sequence_counts: Counter[int]) -> dict[str, Any]:
    values = sorted(sequence_counts)
    gaps: list[dict[str, int]] = []
    missing_slots = 0
    for previous, current in zip(values, values[1:]):
        if current - previous > 1:
            start = previous + 1
            end = current - 1
            count = end - start + 1
            gaps.append({"start": start, "end": end})
            missing_slots += count
    duplicate_count = sum(count - 1 for count in sequence_counts.values() if count > 1)
    return {
        "seq_min": values[0] if values else None,
        "seq_max": values[-1] if values else None,
        "duplicate_seq_count": duplicate_count,
        "internal_seq_gap_ranges": gaps,
        "missing_exported_sequence_slot_count": missing_slots,
    }


def _rank_capture(rank: RankSpec, redact: bool, *, expected_world_hash: str, world_verified: bool) -> dict[str, Any]:
    digest, events, failure = _read_events(rank)
    identity: dict[str, Any] = {
        "global_rank": rank.global_rank,
        "comm_rank": rank.comm_rank,
        "local_rank": rank.local_rank,
        "node_alias": "REDACTED" if redact else rank.node_alias,
    }
    if not redact:
        identity["pid"] = rank.pid

    if events is None:
        return {
            "identity": identity,
            "trace_input": {
                "sha256": digest if digest is not None else "UNKNOWN",
                "parse_status": "UNKNOWN",
                "producer_flush_status": "UNKNOWN",
                "completeness_status": "UNKNOWN",
                "export_failure": failure,
            },
            "exported_window": {
                "status": "UNKNOWN",
                "first_ts": None,
                "last_ts": None,
                "minimum_ts": None,
                "maximum_ts": None,
                "clock_domain": rank.clock.get("domain", "UNKNOWN"),
                "unit": rank.clock.get("unit", "UNKNOWN"),
            },
            "collector_active_window": "UNKNOWN",
            "event_classes": {
                event_class: {
                    "observed_begin_count": "UNKNOWN",
                    "observed_end_count": "UNKNOWN",
                    "attributed_begin_count": "UNKNOWN",
                    "paired_count": "UNKNOWN",
                    "pairing_issues": "UNKNOWN",
                }
                for event_class in EVENT_CLASSES
            },
            "operations": "UNKNOWN",
            "unattributed_collective_begin_count": "UNKNOWN",
            "quarantined_collective_begin_count": "UNKNOWN",
            "collective_begin_issues": "UNKNOWN",
            "bad_pid_event_count": "UNKNOWN",
            "telemetry": _unknown_telemetry(),
        }

    class_stats = _class_stats()
    operations: dict[str, dict[str, Any]] = defaultdict(_operation_stats)
    open_events: dict[tuple[str, str, str], tuple[str, str | None]] = {}
    begin_times: dict[tuple[str, str, str], float | None] = {}
    ambiguous_tokens: dict[tuple[str, str, str], list[tuple[str, str | None]]] = {}
    timestamps: list[float] = []
    bad_pid_event_count = 0
    unattributed_collective_begin_count = 0
    quarantined_collective_begin_count = 0
    collective_begin_issues: Counter[str] = Counter()
    recognized_event_count = 0

    def add_pair_issue(event_class: str, issue: str, operation: str | None = None) -> None:
        class_stats[event_class]["pairing_issues"][issue] += 1
        if event_class == "Coll" and operation:
            operations[operation]["pairing_issues"][issue] += 1

    for event in events:
        ts = _optional_float(event.get("ts"))
        if ts is not None:
            timestamps.append(ts)
        event_class = _event_class(event)
        if event_class is None:
            continue
        phase = event.get("ph")
        if phase not in ("b", "e"):
            continue
        recognized_event_count += 1
        stats = class_stats[event_class]
        if phase == "b":
            stats["observed_begin_count"] += 1
        else:
            stats["observed_end_count"] += 1

        event_pid = _optional_int(event.get("pid"))
        if event_pid != rank.pid:
            bad_pid_event_count += 1
            continue

        operation: str | None = None
        if phase == "b":
            stats["attributed_begin_count"] += 1
            if event_class == "Coll":
                collective = _normalise_collective(event, rank)
                invalid_identity: list[str] = []
                if not world_verified:
                    invalid_identity.append("WORLD_MAPPING_UNVERIFIED")
                elif collective.comm_hash != expected_world_hash:
                    invalid_identity.append("MISSING_COMM_HASH" if collective.comm_hash is None else "COMM_HASH_MISMATCH")
                if "MISSING_COMM_RANK" in collective.metadata_issues or collective.comm_rank != rank.comm_rank:
                    invalid_identity.append("MISSING_COMM_RANK" if "MISSING_COMM_RANK" in collective.metadata_issues else "COMM_RANK_MISMATCH")
                if collective.function is None:
                    invalid_identity.append("MISSING_FUNCTION")

                if invalid_identity:
                    quarantined_collective_begin_count += 1
                    for reason in set(invalid_identity):
                        collective_begin_issues[reason] += 1
                    unattributed_collective_begin_count += 1
                else:
                    operation = collective.function
                    op_stats = operations[operation]
                    op_stats["observed_begin_count"] += 1
                    for parser_issue in collective.metadata_issues:
                        if parser_issue in {"MISSING_SEQ_NUM", "INVALID_SEQ_NUM"}:
                            op_stats["parser_issues"][parser_issue] += 1
                    if collective.seq_num is not None:
                        op_stats["sequence_values"][collective.seq_num] += 1
                    else:
                        op_stats["parser_issues"]["MISSING_OR_INVALID_SEQ_NUM"] += 1

        token = _event_token(event)
        if token is None:
            add_pair_issue(event_class, "MISSING_PAIR_ID", operation)
            continue

        if phase == "b":
            if token in ambiguous_tokens:
                add_pair_issue(event_class, "AMBIGUOUS_BEGIN", operation)
                ambiguous_tokens[token].append((event_class, operation))
                continue
            if token in open_events:
                previous_class, previous_operation = open_events.pop(token)
                begin_times.pop(token, None)
                add_pair_issue(event_class, "DUPLICATE_BEGIN", operation)
                if previous_class != event_class:
                    add_pair_issue(previous_class, "DUPLICATE_BEGIN", previous_operation)
                elif previous_operation and previous_operation != operation:
                    add_pair_issue(previous_class, "DUPLICATE_BEGIN", previous_operation)
                ambiguous_tokens[token] = [(previous_class, previous_operation), (event_class, operation)]
                continue
            open_events[token] = (event_class, operation)
            begin_times[token] = _optional_float(event.get("ts"))
            continue

        if token in ambiguous_tokens:
            add_pair_issue(event_class, "AMBIGUOUS_END")
            for begin_class, begin_operation in ambiguous_tokens.pop(token):
                if begin_class == "Coll" and begin_operation:
                    operations[begin_operation]["pairing_issues"]["AMBIGUOUS_END"] += 1
            continue
        begin_info = open_events.pop(token, None)
        if begin_info is None:
            add_pair_issue(event_class, "ORPHAN_END")
            continue
        begin_class, begin_operation = begin_info
        begin_ts = begin_times.pop(token, None)
        end_ts = _optional_float(event.get("ts"))
        if begin_ts is None or end_ts is None:
            add_pair_issue(begin_class, "UNKNOWN_LOCAL_PAIR_TIME", begin_operation)
        elif end_ts < begin_ts:
            add_pair_issue(begin_class, "REVERSED_LOCAL_PAIR_TIME", begin_operation)
        if begin_class != event_class:
            add_pair_issue(begin_class, "PAIR_CLASS_MISMATCH", begin_operation)
            add_pair_issue(event_class, "PAIR_CLASS_MISMATCH")
            continue
        class_stats[begin_class]["paired_count"] += 1
        if begin_class == "Coll" and begin_operation:
            operations[begin_operation]["paired_count"] += 1

    for event_class, operation in open_events.values():
        add_pair_issue(event_class, "ORPHAN_BEGIN", operation)
    for ambiguous_begins in ambiguous_tokens.values():
        for event_class, operation in ambiguous_begins:
            add_pair_issue(event_class, "AMBIGUOUS_OPEN_AT_EOF", operation)

    rendered_classes: dict[str, Any] = {}
    for event_class, stats in class_stats.items():
        rendered_classes[event_class] = {
            "observation_status": "OBSERVED" if stats["observed_begin_count"] else "UNKNOWN",
            "completeness_status": "UNKNOWN",
            "observed_begin_count": stats["observed_begin_count"],
            "observed_end_count": stats["observed_end_count"],
            "attributed_begin_count": stats["attributed_begin_count"],
            "paired_count": stats["paired_count"],
            "pairing_issues": dict(sorted(stats["pairing_issues"].items())),
        }

    rendered_operations: list[dict[str, Any]] = []
    for operation, stats in sorted(operations.items()):
        sequence = _seq_summary(stats["sequence_values"])
        unknown_sequences = stats["parser_issues"].get("MISSING_OR_INVALID_SEQ_NUM", 0)
        rendered_operations.append({
            "operation": operation,
            "communicator_alias": "world",
            "observed_begin_count": stats["observed_begin_count"],
            "paired_count": stats["paired_count"],
            **sequence,
            "sequence_status": "MISSING" if sequence["internal_seq_gap_ranges"] else "UNKNOWN" if unknown_sequences or not stats["sequence_values"] else "OBSERVED",
            "sequence_completeness_status": "UNKNOWN",
            "unknown_sequence_begin_count": unknown_sequences,
            "pairing_issues": dict(sorted(stats["pairing_issues"].items())),
            "parser_issues": dict(sorted(stats["parser_issues"].items())),
            "gap_interpretation": "MISSING_EXPORTED_SEQUENCE_SLOTS; NOT_PROVEN_COLLECTOR_DROPS",
        })

    exported_window = {
        "status": "OBSERVED" if timestamps else "UNKNOWN",
        "first_ts": timestamps[0] if timestamps else None,
        "last_ts": timestamps[-1] if timestamps else None,
        "minimum_ts": min(timestamps) if timestamps else None,
        "maximum_ts": max(timestamps) if timestamps else None,
        "clock_domain": rank.clock.get("domain", "UNKNOWN"),
        "unit": rank.clock.get("unit", "UNKNOWN"),
        "timestamp_semantics": "RAW_EXPORTED_EVENT_TIMESTAMPS",
    }
    return {
        "identity": identity,
        "trace_input": {
            "sha256": digest,
            "parse_status": "OBSERVED_SUCCESS",
            "producer_flush_status": "UNKNOWN",
            "completeness_status": "UNKNOWN",
            "export_failure": None,
        },
        "exported_window": exported_window,
        "collector_active_window": "UNKNOWN",
        "event_classes": rendered_classes,
        "operations": rendered_operations,
        "unattributed_collective_begin_count": unattributed_collective_begin_count,
        "quarantined_collective_begin_count": quarantined_collective_begin_count,
        "collective_begin_issues": dict(sorted(collective_begin_issues.items())),
        "bad_pid_event_count": bad_pid_event_count,
        "unclassified_event_count": len(events) - recognized_event_count,
        "telemetry": _unknown_telemetry(),
    }


def _unknown_telemetry() -> dict[str, Any]:
    return {
        "scope": "ALL_CLASSES_UNOBSERVED",
        "attempted": "UNKNOWN",
        "emitted": "UNKNOWN",
        "dropped": "UNKNOWN",
        "overwritten": "UNKNOWN",
        "flush": "UNKNOWN",
        "basis": "No explicit source with event-class and window scope was accepted",
    }


def analyze_manifest(manifest_path: Path, *, redact_identifiers: bool = True) -> dict[str, Any]:
    """Analyze trace export quality using validated manifest rank identities.

    Public output is redacted by default. A successful JSON parse proves only
    that an export file was readable; producer flush and full-window coverage
    remain UNKNOWN.
    """
    manifest_path = Path(manifest_path)
    _, rank_specs, details, manifest_issues = load_manifest(manifest_path)
    manifest_hash = _sha256(manifest_path)
    run_id = details["run_id"]
    epoch_value = details["rank_epoch"]
    world_verified = not manifest_issues

    rank_results = [
        _rank_capture(
            rank,
            redact_identifiers,
            expected_world_hash=details["world_comm_hash"],
            world_verified=world_verified,
        )
        for rank in sorted(rank_specs, key=lambda item: (item.global_rank, item.comm_rank))
    ]
    for rank, row in zip(sorted(rank_specs, key=lambda item: (item.global_rank, item.comm_rank)), rank_results):
        row["clocks"] = {
            "host": assess_clock_quality(rank.clock),
            "gpu_channel": assess_clock_quality({"domain": "GPU_GLOBALTIMER", "unit": "ns"}),
            "step": assess_clock_quality({"domain": "CUDA_EVENT_DURATION", "unit": "ms"}),
        }
    readable = sum(row["trace_input"]["parse_status"] == "OBSERVED_SUCCESS" for row in rank_results)
    class_coverage: dict[str, str] = {}
    for event_class in EVENT_CLASSES:
        observed = [row["event_classes"][event_class]["observed_begin_count"] for row in rank_results]
        if any(value == "UNKNOWN" for value in observed):
            class_coverage[event_class] = "UNKNOWN"
        elif sum(observed) > 0:
            class_coverage[event_class] = "OBSERVED"
        else:
            class_coverage[event_class] = "UNKNOWN"

    output: dict[str, Any] = {
        "schema_version": 1,
        "schema_name": "CaptureQuality",
        "classification": "CPU_OFFLINE_CAPTURE_QUALITY_ONLY",
        "run_id": "REDACTED" if redact_identifiers else run_id,
        "rank_epoch": "REDACTED" if redact_identifiers else epoch_value,
        "world": {
            "communicator_alias": "world",
            "membership_status": "VERIFIED" if world_verified else "UNKNOWN",
            "world_size": details["world_size"],
            "communicator_alias_per_operation": "world",
            "member_global_ranks": sorted(member.global_rank for member in details["world_members"]),
            "manifest_precondition_issues": manifest_issues,
        },
        "inputs": {
            "manifest_sha256": manifest_hash if manifest_hash is not None else "UNKNOWN",
            "trace_paths_included": False,
        },
        "summary": {
            "expected_rank_count": details["world_size"],
            "manifest_rank_count": len(rank_specs),
            "trace_parse_success_count": readable,
            "trace_parse_unknown_count": len(rank_results) - readable,
            "event_classes": class_coverage,
            "all_producer_flush_status": "UNKNOWN",
            "all_collector_active_windows": "UNKNOWN",
            "all_capture_counters": "UNKNOWN",
        },
        "interpretation": {
            "sequence_gap_meaning": "MISSING_EXPORTED_SEQUENCE_SLOTS_NOT_PROVEN_COLLECTOR_DROPS",
            "common_sequence_omissions": "UNKNOWN",
            "head_coverage": "UNKNOWN",
            "tail_coverage": "UNKNOWN",
            "unobserved_operations": "UNKNOWN",
            "unobserved_event_classes": {
                event_class: "UNKNOWN" for event_class, status in class_coverage.items() if status == "UNKNOWN"
            },
            "continuous_sequences_do_not_prove_completeness": True,
            "same_gap_on_all_ranks_does_not_prove_common_collector_loss": True,
            "raw_exported_window_vs_collector_active_window": "UNKNOWN",
        },
        "ranks": rank_results,
    }
    if not redact_identifiers:
        output["world"]["communicator_hash"] = details["world_comm_hash"]
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="validated rank manifest used by G1-01")
    parser.add_argument("-o", "--output", type=Path, help="write JSON summary to this path (default: stdout)")
    parser.add_argument("--no-redact-identifiers", action="store_false", dest="redact_identifiers")
    parser.set_defaults(redact_identifiers=True)
    args = parser.parse_args(argv)
    try:
        result = analyze_manifest(args.manifest, redact_identifiers=args.redact_identifiers)
    except InputError as exc:
        print(f"g1_02_capture_quality: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
