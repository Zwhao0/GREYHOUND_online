"""Private, opt-in G2-01 injection plan and truth handling (standard library only)."""

from collections import Counter
import json
import os
from pathlib import Path
import re
import tempfile
import time


PLAN_SCHEMA = "g2-01-plan-v1"
TRUTH_SCHEMA = "g2-01-truth-v1"
DELAY_S = 0.020
EPISODE_COUNT = 8
RANKS = (0, 1, 2, 3)
_NONCE_RE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


def validate_capture_bounds(*, steps, warmup, world_size):
    """Enforce the fixed four-rank G2-01 capture envelope."""
    if world_size != 4:
        raise ValueError("G2-01 capture requires exactly four ranks")
    if warmup != 5:
        raise ValueError("G2-01 capture requires exactly five warmup steps")
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 40:
        raise ValueError("G2-01 measured steps must be in [1, 40]")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("G2-01 plan JSON contains a duplicate key")
        result[key] = value
    return result


def load_plan(path, *, steps, warmup, world_size):
    """Load and validate an explicitly supplied private plan.

    Measured step indexes are zero-based. Episodes need at least one measured
    step between them so the eight episodes remain separated.
    """
    validate_capture_bounds(steps=steps, warmup=warmup, world_size=world_size)

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("could not read G2-01 plan JSON") from exc
    if not isinstance(document, dict) or set(document) != {"schema", "nonce", "episodes"}:
        raise ValueError("G2-01 plan must contain exactly schema, nonce, and episodes")
    if document["schema"] != PLAN_SCHEMA:
        raise ValueError("unsupported G2-01 plan schema")
    nonce = document["nonce"]
    if not isinstance(nonce, str) or not _NONCE_RE.fullmatch(nonce):
        raise ValueError("G2-01 plan nonce must be 1-128 letters, digits, '_' or '-'")
    episodes = document["episodes"]
    if not isinstance(episodes, list) or len(episodes) != EPISODE_COUNT:
        raise ValueError("G2-01 plan must contain exactly eight episodes")

    validated = []
    for episode in episodes:
        if not isinstance(episode, dict) or set(episode) != {"step", "rank", "delay_s"}:
            raise ValueError("each G2-01 episode must contain exactly step, rank, and delay_s")
        step, rank, delay = episode["step"], episode["rank"], episode["delay_s"]
        if not isinstance(step, int) or isinstance(step, bool) or not 0 <= step < steps:
            raise ValueError("G2-01 episode step is outside the measured-step range")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank not in RANKS:
            raise ValueError("G2-01 episode rank must be in [0, 3]")
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or delay != DELAY_S:
            raise ValueError("G2-01 episode delay must equal 0.020 seconds")
        validated.append({"step": step, "rank": rank, "delay_s": DELAY_S})

    ordered_steps = sorted(episode["step"] for episode in validated)
    if len(set(ordered_steps)) != EPISODE_COUNT:
        raise ValueError("G2-01 episode steps must be distinct")
    if any(right - left < 2 for left, right in zip(ordered_steps, ordered_steps[1:])):
        raise ValueError("G2-01 episodes must have at least one measured step between them")
    if Counter(episode["rank"] for episode in validated) != Counter({rank: 2 for rank in RANKS}):
        raise ValueError("G2-01 plan must assign exactly two episodes to each rank")
    return {"schema": PLAN_SCHEMA, "nonce": nonce, "episodes": validated}


def episode_for(plan, *, step, rank):
    """Return this process's episode for a measured step, if any."""
    if plan is None:
        return None
    return next((episode for episode in plan["episodes"]
                 if episode["step"] == step and episode["rank"] == rank), None)


def sleep_for_episode(episode):
    """Perform the scheduled host sleep and return its private actual timing."""
    if episode is None:
        return None
    sleep_start_ns = time.monotonic_ns()
    time.sleep(episode["delay_s"])
    sleep_end_ns = time.monotonic_ns()
    return {
        "scheduled_delay_s": episode["delay_s"],
        "sleep_start_monotonic_ns": sleep_start_ns,
        "sleep_end_monotonic_ns": sleep_end_ns,
        "actual_delay_s": (sleep_end_ns - sleep_start_ns) / 1_000_000_000,
    }


def ensure_separate_output(truth_output, public_output):
    """Reject a truth directory that overlaps the ordinary capture output."""
    truth = Path(truth_output).resolve()
    public = Path(public_output).resolve()
    if truth == public or truth in public.parents or public in truth.parents:
        raise ValueError("G2-01 truth output must be separate from capture output")


def write_rank_truth(directory, *, rank, steps, warmup, plan, step_boundaries):
    """Write one owner-only per-rank truth file, atomically."""
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    record = {
        "schema": TRUTH_SCHEMA,
        "rank": rank,
        "steps": steps,
        "warmup": warmup,
        "plan_nonce": plan["nonce"] if plan is not None else None,
        "step_boundaries": step_boundaries,
    }
    target = output / f"rank-{rank}.json"
    fd, temporary_name = tempfile.mkstemp(prefix=f".rank-{rank}-", suffix=".tmp", dir=output)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link publishes the complete file atomically and fails if a
        # rank truth file already exists, preserving create-exclusive behavior.
        os.link(temporary_name, target)
        os.unlink(temporary_name)
        return target
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
