#!/usr/bin/env python3
"""Blind, offline G2-01 Host-arrival prototype; CPU logic is not GPU proof.

Input is sanitized g2-01-host-intervals-v1 JSON only. No episode/step,
truth, injection, seed, runtime logs or file references are consumed. Each
matched instance supplies all ranks' BOUNDED Host COLL-begin intervals on
one audited reference clock. These are not GPU-kernel start timestamps.

The baseline must be a separately captured HEALTHY_BASELINE with the same
workload, configuration, rank mapping, membership and collective metadata.
For each rank, healthy lag is relative to its latest peer in that instance.
A candidate must start strictly after every peer and exceed the maximum
healthy upper lag by >10ms (fixed before the 20ms pilot). No duration score
or midpoint order is used. Finite baseline coverage, correlated delays and
Host callback latency limit this to a scoped ROOT_CANDIDATE, not proof of
physical origin. Unresolved overlap, missingness and quality fail closed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

SCHEMA = 'g2-01-host-intervals-v1'
DELAY_MARGIN_NS = 10_000_000
METADATA = ('function', 'count', 'datatype', 'algorithm', 'protocol', 'n_channels')
DOC_FIELDS = {'schema', 'role', 'run_id', 'rank_epoch', 'reference_clock', 'unit',
              'expected_ranks', 'quality', 'comparability', 'instances'}
INSTANCE_FIELDS = {'comm_hash', 'seq_num', 'status', 'ranks', *METADATA}
ROW_FIELDS = {'rank', 'status', 'start', 'end', 'source_ns'}


def _integer(value):
    return type(value) is int and value >= 0


def _interval(value):
    return (isinstance(value, list) and len(value) == 2
            and all(_integer(x) for x in value) and value[0] <= value[1])


def _document_reason(doc, role):
    if not isinstance(doc, dict):
        return 'INVALID_DOCUMENT'
    if set(doc) - DOC_FIELDS:
        return 'UNSUPPORTED_INPUT_FIELDS'
    if doc.get('schema') != SCHEMA or doc.get('role') != role or doc.get('unit') != 'ns':
        return 'SCHEMA_ROLE_OR_UNIT'
    if any(not isinstance(doc.get(k), str) or not doc[k] for k in
           ('run_id', 'rank_epoch', 'reference_clock')):
        return 'MISSING_CLOCK_OR_IDENTITY'
    ranks = doc.get('expected_ranks')
    if (not isinstance(ranks, list) or len(ranks) < 2
            or not all(_integer(r) for r in ranks) or len(set(ranks)) != len(ranks)):
        return 'INVALID_MEMBERSHIP'
    q = doc.get('quality')
    if (not isinstance(q, dict) or set(q) - {'status', 'complete', 'dropped', 'truncated'}
            or q.get('status') != 'BOUNDED' or q.get('complete') is not True
            or ('dropped' in q and (type(q['dropped']) is not int or q['dropped'] != 0))
            or ('truncated' in q and q['truncated'] is not False)):
        return 'CAPTURE_QUALITY'
    c = doc.get('comparability')
    if (not isinstance(c, dict) or set(c) != {'workload', 'configuration', 'rank_mapping'}
            or any(not isinstance(v, str) or not v for v in c.values())):
        return 'COMPARABILITY_UNDECLARED'
    if not isinstance(doc.get('instances'), list) or not doc['instances']:
        return 'NO_INSTANCES'
    return None


def _instance_reason(instance, expected):
    if not isinstance(instance, dict) or set(instance) - INSTANCE_FIELDS:
        return 'INVALID_INSTANCE_FIELDS'
    if instance.get('status') != 'MATCHED':
        return 'UNMATCHED_INSTANCE'
    if (not isinstance(instance.get('comm_hash'), str) or not instance['comm_hash']
            or not _integer(instance.get('seq_num'))):
        return 'INVALID_COLLECTIVE_KEY'
    if (not _integer(instance.get('count')) or not _integer(instance.get('n_channels'))
            or instance['n_channels'] < 1
            or any(not isinstance(instance.get(k), str) or not instance[k]
                   or instance[k] == 'UNKNOWN' for k in ('function', 'datatype', 'algorithm', 'protocol'))):
        return 'INCOMPLETE_COLLECTIVE_METADATA'
    rows = instance.get('ranks')
    if (not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows)
            or any(not _integer(r.get('rank')) for r in rows)
            or len(rows) != len(expected) or {r['rank'] for r in rows} != set(expected)):
        return 'MISSING_OR_DUPLICATE_RANK'
    for row in rows:
        if set(row) - ROW_FIELDS:
            return 'INVALID_RANK_FIELDS'
        if row.get('status') != 'BOUNDED' or not _interval(row.get('start')):
            return 'INTERVAL_QUALITY'
        if 'source_ns' in row and not _integer(row['source_ns']):
            return 'INVALID_LOCAL_TIMESTAMP'
        if 'end' in row and (not _interval(row['end']) or row['end'][0] < row['start'][1]):
            return 'INVALID_END_INTERVAL'
    return None


def _key(instance):
    return tuple(instance[k] for k in METADATA)


def _lag(rows, rank):
    start = rows[rank]
    peers = [v for k, v in rows.items() if k != rank]
    return [start[0] - max(p[1] for p in peers),
            start[1] - max(p[0] for p in peers)]


def locate(observed, baseline=None):
    """Return every collective's blind decision, without episode aggregation."""
    reason = _document_reason(observed, 'OBSERVED')
    result = dict(schema='g2-01-blind-predictions-v1',
                  method='STRICT_HOST_LATE_ARRIVAL_V1', delay_margin_ns=DELAY_MARGIN_NS,
                  timing_semantics='HOST_COLL_BEGIN_NOT_GPU_KERNEL_START',
                  status='UNKNOWN', reasons=[], instances=[])
    if reason:
        result['reasons'] = [reason]
        return result
    baseline_reason = _document_reason(baseline, 'HEALTHY_BASELINE')
    if baseline_reason:
        baseline_reason = ('BASELINE_QUALITY' if baseline_reason == 'CAPTURE_QUALITY'
                           else 'BASELINE_UNAVAILABLE')
    elif (set(observed['expected_ranks']) != set(baseline['expected_ranks'])
          or observed['comparability'] != baseline['comparability']
          or observed['run_id'] == baseline['run_id']):
        baseline_reason = 'BASELINE_UNAVAILABLE'
    healthy = {}
    if not baseline_reason:
        for instance in baseline['instances']:
            if _instance_reason(instance, baseline['expected_ranks']):
                # Do not silently select only clean baseline instances.
                baseline_reason = 'BASELINE_QUALITY'
                break
            rows = {r['rank']: r['start'] for r in instance['ranks']}
            entry = healthy.setdefault(_key(instance), {r: [] for r in rows})
            for rank in rows:
                entry[rank].append(max(0, _lag(rows, rank)[1]))
    keys = Counter((i.get('comm_hash'), i.get('function'), i.get('seq_num'))
                   for i in observed['instances'] if isinstance(i, dict)
                   and all(isinstance(i.get(k), (str, int)) for k in ('comm_hash', 'function', 'seq_num')))
    for instance in observed['instances']:
        row = dict(status='UNKNOWN', rank=None, reasons=[], evidence=None)
        if isinstance(instance, dict):
            row.update({k: instance.get(k) for k in ('comm_hash', 'function', 'seq_num')})
        problem = _instance_reason(instance, observed['expected_ranks'])
        if not problem and keys[(instance['comm_hash'], instance['function'], instance['seq_num'])] != 1:
            problem = 'DUPLICATE_INSTANCE'
        if not problem:
            problem = baseline_reason or (None if _key(instance) in healthy else 'BASELINE_UNAVAILABLE')
        if problem:
            row['reasons'] = [problem]
        else:
            starts = {r['rank']: r['start'] for r in instance['ranks']}
            latest = [rank for rank, start in starts.items()
                      if all(peer[1] < start[0] for r, peer in starts.items() if r != rank)]
            if len(latest) != 1:
                row['reasons'] = ['OVERLAP_OR_NO_STRICT_LATEST']
            else:
                rank = latest[0]
                lag = _lag(starts, rank)
                samples = healthy[_key(instance)][rank]
                upper = max(samples)
                row['evidence'] = dict(late_rank=rank, arrival_lag_ns=lag,
                                       healthy_same_rank_max_upper_ns=upper,
                                       healthy_instances=len(samples),
                                       excess_lower_ns=lag[0] - upper,
                                       strict_later_than=sorted(r for r in starts if r != rank))
                if lag[0] - upper > DELAY_MARGIN_NS:
                    row.update(status='ROOT_CANDIDATE', rank=rank,
                               reasons=['STRICT_LATE_HOST_ARRIVAL_ABOVE_HEALTHY_BASELINE'])
                else:
                    row['reasons'] = ['NO_20MS_SCALE_EXCESS_ESTABLISHED']
        result['instances'].append(row)
    result['summary'] = dict(Counter(r['status'] for r in result['instances']))
    result['status'] = 'COMPLETE'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('observed', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    observed_bytes = args.observed.read_bytes()
    baseline_bytes = args.baseline.read_bytes() if args.baseline else None
    result = locate(json.loads(observed_bytes), json.loads(baseline_bytes) if baseline_bytes else None)
    result['input_sha256'] = dict(observed=hashlib.sha256(observed_bytes).hexdigest(),
                                 baseline=hashlib.sha256(baseline_bytes).hexdigest() if baseline_bytes else None)
    result['locator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
