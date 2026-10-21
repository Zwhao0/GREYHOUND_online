#!/usr/bin/env python3
"""CPU-only clock contract validation; this module never samples or calibrates clocks.

Existing trace clocks are UNSAFE for cross-rank subtraction, even when their
local duration is useful. No captured process origin/control exchange permits
retrospective alignment of the G1-01 traces.

Synthetic exchange schema (all timestamps in the declared, common unit):
  classification=CPU_SYNTHETIC, transport=INDEPENDENT_CONTROL,
  reference={domain, domain_id, epoch, unit}, source={same keys},
  t1=reference send, t2=source receive, t3=source send, t4=reference receive,
  nonnegative_one_way_delay_assumed=true, timestamp_error_bound >= 0,
  drift_bound_ppm >= 0, valid_from, valid_until (reference clock coordinates).
The rate bound is on source-minus-reference offset per reference-clock unit.
The timestamp error bound applies to EACH timestamp in either domain. It and
the drift bound are assumed mathematical inputs, never measured by this tool.
The window must contain the complete exchange. Source offset is source minus
reference; map source timestamps by subtracting its bounded offset. One-way
symmetry is NOT assumed. Bounds are deliberately widened for drift and error.

compare_fixture_times accepts first in reference and second in source, each
{timestamp, domain, domain_id, epoch, unit}; it returns second-minus-first as
an interval. The contract must additionally declare max_uncertainty (maximum
allowed half-width, in the same unit); inadequate budgets are UNSAFE. Strict order requires the whole interval to exclude zero. Every
successful result remains calibration=UNKNOWN, actual_cross_rank_comparable=false.
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

PIN = "593de54e52679b51428571c13271e2ea9f91b1b1"
SOURCES = {
    "host": f"https://github.com/NVIDIA/nccl/blob/{PIN}/ext-profiler/example/plugin.c#L41-L44",
    "export": f"https://github.com/NVIDIA/nccl/blob/{PIN}/ext-profiler/example/print_event.c#L109-L126",
    "abi": "https://github.com/NVIDIA/nccl/blob/73cf112295c33aee2b895f329f592f2a9b4b0f97/src/plugin/profiler/profiler_v4.cc#L64-L68",
    "captured_evidence": "docs/G1-01-RESULTS.md",
}
UNITS = {"ns", "us", "ms", "s"}
IDENTITY_KEYS = ("domain", "domain_id", "epoch", "unit")


def _unsafe(reason: str) -> dict[str, Any]:
    return {"status": "UNSAFE", "calibration": "UNKNOWN",
            "actual_cross_rank_comparable": False, "usable_for_cross_rank": False,
            "uncertainty": "UNKNOWN", "reasons": [reason]}


def assess_clock_quality(record: Mapping[str, Any]) -> dict[str, Any]:
    """Describe captured local semantics without inferring alignment or identity."""
    if not isinstance(record, Mapping):
        return _unsafe("clock record must be an object")
    clock = record.get("clock", record)
    if not isinstance(clock, Mapping):
        return _unsafe("clock must be an object")
    domain = clock.get("domain", "UNKNOWN")
    if not isinstance(domain, str):
        domain = "UNKNOWN"
    meanings = {
        "PROCESS_CLOCK_MONOTONIC_RELATIVE": "per-process relative Host CLOCK_MONOTONIC; Chrome GPU category ts is also Host observation",
        "GPU_GLOBALTIMER": "raw per-GPU globaltimer channel-work timestamps, not complete kernel launch times",
        "CUDA_EVENT_DURATION": "local GPU elapsed duration, not an absolute timestamp or Host/GPU alignment",
    }
    result = _unsafe("no measured cross-rank alignment/error bound; existing trace origins and independent-control timestamps were not captured")
    result.update({"domain": domain, "unit": clock.get("unit") if isinstance(clock.get("unit"), str) else "UNKNOWN",
                   "domain_id": clock.get("domain_id") if isinstance(clock.get("domain_id"), str) else "UNKNOWN",
                   "epoch": clock.get("epoch") if isinstance(clock.get("epoch"), str) else "UNKNOWN",
                   "semantics": meanings.get(domain, "UNKNOWN"),
                   "provenance": SOURCES.copy(), "test_classification": "CPU"})
    return result


def _number(value: Any, name: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    except OverflowError as exc:
        raise ValueError(f"{name} is too large") from exc
    return Decimal(value)  # float conversion is exact, not a rounded display string


def _identity(value: Any, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} identity is required")
    out = {}
    for key in IDENTITY_KEYS:
        item = value.get(key)
        if not isinstance(item, str) or not item.strip() or item.upper() in {"UNKNOWN", "UNSAFE"}:
            raise ValueError(f"{name}.{key} must be explicitly known")
        out[key] = item
    if out["unit"] not in UNITS:
        raise ValueError(f"{name}.unit is unsupported")
    return out


def _outward(value: Decimal, upward: bool) -> float:
    result = math.nextafter(float(value), math.inf if upward else -math.inf)
    if not math.isfinite(result):
        raise ValueError("derived interval is not finite")
    return result


def _validated(exchange: Mapping[str, Any]) -> tuple[dict, dict, Decimal, Decimal, Decimal, Decimal]:
    if not isinstance(exchange, Mapping):
        raise ValueError("exchange must be an object")
    if exchange.get("classification") != "CPU_SYNTHETIC":
        raise ValueError("only explicitly CPU_SYNTHETIC fixtures are supported")
    if exchange.get("transport") != "INDEPENDENT_CONTROL":
        raise ValueError("independent control path must be explicit; training world exchanges are unsupported")
    if exchange.get("nonnegative_one_way_delay_assumed") is not True:
        raise ValueError("explicit nonnegative one-way delay assumption is required")
    reference = _identity(exchange.get("reference"), "reference")
    source = _identity(exchange.get("source"), "source")
    if reference["unit"] != source["unit"]:
        raise ValueError("source/reference units must match; conversion is not inferred")
    if reference["domain_id"] == source["domain_id"]:
        raise ValueError("distinct source/reference domain identities are required")
    if reference["domain"] != "HOST_MONOTONIC" or source["domain"] != "HOST_MONOTONIC":
        raise ValueError("fixture exchange supports independent Host clocks only; GPU/elapsed domains cannot be calibrated")
    t1, t2, t3, t4 = [_number(exchange.get(key), key) for key in ("t1", "t2", "t3", "t4")]
    start = _number(exchange.get("valid_from"), "valid_from")
    stop = _number(exchange.get("valid_until"), "valid_until")
    error = _number(exchange.get("timestamp_error_bound"), "timestamp_error_bound")
    drift = _number(exchange.get("drift_bound_ppm"), "drift_bound_ppm")
    if error < 0 or drift < 0 or drift >= 1_000_000:
        raise ValueError("error must be nonnegative and drift must be in [0,1000000) ppm")
    if t4 < t1 or t3 < t2 or (t4 - t1) - (t3 - t2) < 0:
        raise ValueError("noncausal exchange or negative causal RTT")
    if not start <= t1 <= t4 <= stop:
        raise ValueError("validity window must contain the complete reference exchange")
    # At zero drift/error, causality gives theta in [t3-t4,t2-t1].
    # Widen for both endpoint timestamp errors and offset evolution over the
    # full exchange plus the requested window; do not fit a symmetric midpoint.
    horizon = max(abs(start - t1), abs(stop - t1)) + (t4 - t1) + 2 * error
    padding = 2 * error + horizon * drift / 1_000_000
    lower, upper = t3 - t4 - padding, t2 - t1 + padding
    if lower > upper:
        raise ValueError("empty offset interval")
    return reference, source, lower, upper, start, stop


def evaluate_four_timestamp_fixture(exchange: Mapping[str, Any]) -> dict[str, Any]:
    """Bound a declared fixture only; unknown or invalid inputs fail closed."""
    try:
        with localcontext() as context:
            context.prec = 3000
            reference, source, lower, upper, start, stop = _validated(exchange)
            return {"status": "BOUNDED", "calibration": "UNKNOWN",
                    "actual_cross_rank_comparable": False, "classification": "CPU_SYNTHETIC",
                    "scope": "fixture mathematical assumptions only; not measured calibration",
                    "reference": reference, "source": source,
                    "offset_source_minus_reference": [_outward(lower, False), _outward(upper, True)],
                    "validity_reference": [exchange["valid_from"], exchange["valid_until"]],
                    "unit": reference["unit"], "reasons": []}
    except (ValueError, ArithmeticError, TypeError) as exc:
        return _unsafe(str(exc))


def compare_fixture_times(first: Mapping[str, Any], second: Mapping[str, Any],
                          contract: Mapping[str, Any]) -> dict[str, Any]:
    """Compare two fixture instants only when the complete mapped interval is valid."""
    try:
        with localcontext() as context:
            context.prec = 3000
            ref, src, lower, upper, start, stop = _validated(contract)
            if _identity(first, "first") != ref or _identity(second, "second") != src:
                raise ValueError("comparison domain/epoch/reference/unit mismatch")
            a = _number(first.get("timestamp"), "first.timestamp")
            b = _number(second.get("timestamp"), "second.timestamp")
            error = _number(contract.get("timestamp_error_bound"), "timestamp_error_bound")
            mapped_low, mapped_high = b - upper - error, b - lower + error
            if not start <= a - error <= a + error <= stop or not start <= mapped_low <= mapped_high <= stop:
                raise ValueError("comparison timestamp uncertainty extends outside validity window")
            low, high = mapped_low - a - error, mapped_high - a + error
            budget = _number(contract.get("max_uncertainty"), "max_uncertainty")
            if budget < 0:
                raise ValueError("max_uncertainty must be nonnegative")
            interval = [_outward(low, False), _outward(high, True)]
            # Include serialization rounding in the budget and reported order.
            half_width = (Decimal(interval[1]) - Decimal(interval[0])) / 2
            if half_width > budget:
                raise ValueError("comparison uncertainty exceeds explicit max_uncertainty budget")
            result = evaluate_four_timestamp_fixture(contract)
            result.update({"second_minus_first": interval,
                           "uncertainty_half_width": _outward(half_width, True),
                           "order": "SECOND_AFTER_FIRST" if interval[0] > 0 else "SECOND_BEFORE_FIRST" if interval[1] < 0 else "UNKNOWN",
                           "comparison_uncertainty": "full offset interval plus both timestamp error bounds"})
            return result
    except (ValueError, ArithmeticError, TypeError) as exc:
        return _unsafe(str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--fixture", action="store_true", help="validate synthetic four-timestamp exchange")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = evaluate_four_timestamp_fixture(data) if args.fixture else assess_clock_quality(data)
    except (OSError, ValueError) as exc:
        result = _unsafe(f"input error: {exc}")
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0 if result["status"] == "BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
