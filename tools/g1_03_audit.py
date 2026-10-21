"""Conservatively validate per-class profiler audit JSON (CPU/offline only).

This report describes plugin callback telemetry. It does not estimate total
NCCL operations or infer exact loss from missing/overwritten events.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any


CLASSES = ("Group", "Coll", "KernelCh")
COUNTERS = ("callback_attempted", "pool_accepted", "known_pool_drop", "parent_rejected",
            "guard_rejected", "exported", "overwritten")
CONSERVATION_COUNTERS = COUNTERS[:5]
IDENTITY_FIELDS = ("run_id", "rank_epoch", "node_alias", "pid", "comm_rank", "comm_hash",
                   "time_namespace", "pid_namespace", "boot_id")
_SAFE_ALIAS = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class AuditInputError(ValueError):
    """Input is not a JSON object that can be audited."""


def parse_audit(source: str | bytes | Mapping[str, Any]) -> dict[str, Any]:
    """Parse JSON or accept a decoded record, then return a sanitized report."""
    if isinstance(source, Mapping):
        record = source
    else:
        try:
            record = json.loads(source)
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise AuditInputError("audit input is not valid JSON") from exc
    if not isinstance(record, Mapping):
        raise AuditInputError("audit input must be a JSON object")
    return validate_audit(record)


def _counter(value: Any) -> tuple[int | str, str]:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value, "OBSERVED"
    if value == "UNKNOWN":
        return "UNKNOWN", "UNKNOWN"
    return "UNKNOWN", "MISSING" if value is None else "UNKNOWN"


def _safe_status(value: Any, success: set[str], failure: set[str]) -> str:
    if not isinstance(value, str):
        return "UNKNOWN"
    normalized = value.strip().upper()
    if normalized in success:
        return "OBSERVED_SUCCESS"
    if normalized in failure:
        return "FAILED"
    return "UNKNOWN"


def _class_report(name: str, raw: Any, export_ok: bool) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {
            "status": "MISSING" if raw is None else "UNKNOWN",
            "counters": {key: "UNKNOWN" for key in COUNTERS},
            "counter_status": {key: "MISSING" for key in COUNTERS},
            "callback_conservation": "UNKNOWN",
            "exported_le_accepted": "UNKNOWN",
            "flush_status": "UNKNOWN",
            "source_status": "MISSING",
        }

    counters: dict[str, int | str] = {}
    counter_status: dict[str, str] = {}
    for key in COUNTERS:
        counters[key], counter_status[key] = _counter(raw.get(key))

    # These counters share a start-callback handle unit in the audited source.
    # KernelCh accepted handles are embedded timer-slot handles, not pool slots.
    if all(counter_status[key] == "OBSERVED" for key in CONSERVATION_COUNTERS):
        conservation = (
            "OBSERVED"
            if counters["callback_attempted"] == sum(counters[key] for key in CONSERVATION_COUNTERS[1:])
            else "MISMATCH"
        )
    else:
        conservation = "UNKNOWN"

    if not export_ok:
        if counter_status["exported"] == "OBSERVED":
            counters["exported"] = "UNKNOWN"
            counter_status["exported"] = "UNKNOWN"

    scopes = raw.get("unit_scopes")
    if isinstance(scopes, Mapping):
        accepted_scope = scopes.get("pool_accepted")
        exported_scope = scopes.get("exported")
    else:
        accepted_scope = exported_scope = raw.get("unit_scope")
    if export_ok and (
        isinstance(accepted_scope, str)
        and accepted_scope
        and accepted_scope == exported_scope
        and counter_status["pool_accepted"] == counter_status["exported"] == "OBSERVED"
    ):
        exported_bound = "OBSERVED" if counters["exported"] <= counters["pool_accepted"] else "MISMATCH"
    else:
        exported_bound = "UNKNOWN"

    flush = _safe_status(raw.get("flush_status", raw.get("flush")),
                         {"OK", "SUCCESS", "FLUSHED", "COMPLETE", "COMPLETED", "OBSERVED_SUCCESS"},
                         {"FAILED", "ERROR", "FLUSH_FAILED"})
    source_status = "OBSERVED" if isinstance(raw.get("source"), str) and raw["source"].strip() else "MISSING"
    class_status = "OBSERVED" if any(counter_status[key] == "OBSERVED" for key in COUNTERS) else "UNKNOWN"
    return {
        "status": class_status,
        "counters": counters,
        "counter_status": counter_status,
        "callback_conservation": conservation,
        "exported_le_accepted": exported_bound,
        "flush_status": flush,
        "source_status": source_status,
    }


def validate_audit(record: Mapping[str, Any], expected: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a sanitized validation summary; never return private identity text."""
    if not isinstance(record, Mapping):
        raise AuditInputError("audit input must be a JSON object")

    issues: list[str] = []
    version = record.get("schema_version")
    schema_status = "OBSERVED" if version == 1 and not isinstance(version, bool) else "UNKNOWN"
    if schema_status == "UNKNOWN":
        issues.append("SCHEMA_VERSION_UNKNOWN")

    alias = record.get("node_alias")
    safe_alias = alias if isinstance(alias, str) and _SAFE_ALIAS.fullmatch(alias) else "UNKNOWN"
    comm_rank = record.get("comm_rank")
    safe_rank: int | str = comm_rank if isinstance(comm_rank, int) and not isinstance(comm_rank, bool) and comm_rank >= 0 else "UNKNOWN"
    origin = record.get("origin_monotonic_ns")
    safe_origin: int | str = origin if isinstance(origin, int) and not isinstance(origin, bool) and origin >= 0 else "UNKNOWN"
    clock_api = "CLOCK_MONOTONIC" if record.get("clock_api") in {
        "CLOCK_MONOTONIC", "clock_gettime(CLOCK_MONOTONIC)"
    } else "UNKNOWN"
    if clock_api == "UNKNOWN":
        issues.append("CLOCK_API_UNKNOWN")

    mapping: dict[str, str] = {}
    expected = expected or {}
    for key in IDENTITY_FIELDS:
        actual = record.get(key)
        if key not in expected:
            mapping[key] = "NOT_CHECKED"
        elif actual is None:
            mapping[key] = "MISSING"
        elif actual == expected[key]:
            mapping[key] = "MATCH"
        else:
            mapping[key] = "MISMATCH"
            issues.append(f"{key.upper()}_MISMATCH")
    if any(value == "MISMATCH" for value in mapping.values()):
        mapping_status = "MISMATCH"
    elif any(value == "MISSING" for value in mapping.values()):
        mapping_status = "UNKNOWN"
    elif any(value == "MATCH" for value in mapping.values()):
        mapping_status = "OBSERVED"
    else:
        mapping_status = "NOT_CHECKED"

    raw_export = record.get("export")
    raw_export = raw_export if isinstance(raw_export, Mapping) else {}
    export_flags = {key: raw_export.get(key) if isinstance(raw_export.get(key), bool) else "UNKNOWN"
                    for key in ("file_open_ok", "write_ok", "close_ok")}
    all_export_flags_ok = all(value is True for value in export_flags.values())
    declared_export = _safe_status(raw_export.get("status"), {"OK", "SUCCESS", "EXPORTED"}, {"FAILED", "ERROR"})
    if any(value is False for value in export_flags.values()) or declared_export == "FAILED":
        export_status = "FAILED"
    elif all_export_flags_ok:
        export_status = "OBSERVED_SUCCESS"
    else:
        export_status = "UNKNOWN"
    if export_status == "FAILED":
        for key, value in export_flags.items():
            if value is False:
                issues.append(f"EXPORT_{key.removesuffix('_ok').upper()}_FAILED")
    flags_known = all(value != "UNKNOWN" for value in export_flags.values())
    if flags_known and declared_export != "UNKNOWN" and declared_export != export_status:
        issues.append("EXPORT_STATUS_MISMATCH")

    raw_classes = record.get("classes")
    classes = {
        name: _class_report(name, raw_classes.get(name) if isinstance(raw_classes, Mapping) else None,
                            all_export_flags_ok and declared_export != "FAILED")
        for name in CLASSES
    }
    if not isinstance(raw_classes, Mapping):
        issues.append("CLASS_TELEMETRY_MISSING")
    for name, class_report in classes.items():
        if class_report["counters"]["exported"] == "UNKNOWN":
            raw_class = raw_classes.get(name) if isinstance(raw_classes, Mapping) else None
            if isinstance(raw_class, Mapping) and isinstance(raw_class.get("exported"), int) and not isinstance(raw_class.get("exported"), bool):
                issues.append("EXPORTED_COUNT_WITHOUT_SUCCESSFUL_EXPORT")

    return {
        "schema_version": 1 if schema_status == "OBSERVED" else "UNKNOWN",
        "schema_status": schema_status,
        "identity": {"node_alias": safe_alias, "comm_rank": safe_rank, "origin_monotonic_ns": safe_origin,
                     "clock_api": clock_api,
                     "resolution_ns": _counter(record.get("resolution_ns"))[0],
                     "origin_mapping_error_ns": _counter(record.get("origin_mapping_error_ns"))[0],
                     "active_until_monotonic_ns": _counter(record.get("active_until_monotonic_ns"))[0]},
        "mapping_status": mapping_status,
        "mapping_checks": mapping,
        "classes": classes,
        "export": {**export_flags, "status": export_status},
        "callback_attempted_is_nccl_total": False,
        "issues": sorted(set(issues)),
    }
