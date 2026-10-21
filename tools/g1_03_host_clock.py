#!/usr/bin/env python3
"""Independent bounded TCP CLOCK_MONOTONIC collector; PRIVATE raw evidence.

No training world, GPU calls, or training threads. Client is reference, server
is source. Run once before and once after training. Four stamps include all
serialization/parsing/scheduling latency; no path symmetry is assumed. A clock
resolution is NOT a timestamp accuracy bound. Two sampled phases do NOT bound
between-sample clock rate. This verifier uses only a broad causal envelope
for the training window, with UNSAFE when its finite uncertainty exceeds budget.
Narrow endpoint envelopes require a constant-offset during exchange assumption.
A separate broad causal mapping uses only monotonicity and nonnegative delays.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
import time
from pathlib import Path

CLASSIFICATION = "REAL_HOST_CONTROL"
API = "clock_gettime(CLOCK_MONOTONIC)"
MAX_SAMPLES = 32
MAX_PACKET = 16384


def now():
    return time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def metadata(run, epoch, node):
    return {"run": run, "epoch": epoch, "node": node, "pid": os.getpid(),
            "pid_namespace": os.readlink('/proc/self/ns/pid'),
            "time_namespace": os.readlink('/proc/self/ns/time'),
            "boot_id": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            "clock_api": API, "resolution_ns": math.ceil(time.clock_getres(time.CLOCK_MONOTONIC) * 1e9)}


def _limits(count, timeout):
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_SAMPLES:
        raise ValueError(f'count must be 1..{MAX_SAMPLES}')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError('timeout must be finite in (0,120] seconds')


def _remaining(sock, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('control collection deadline expired')
    sock.settimeout(remaining)


def _send(sock, value, deadline):
    _remaining(sock, deadline)
    data = json.dumps(value, separators=(',', ':'), allow_nan=False).encode() + b'\n'
    if len(data) > MAX_PACKET:
        raise ValueError('control packet too large')
    sock.sendall(data)


def _receive(sock, deadline):
    data = bytearray()
    # Single byte framing avoids hidden buffered receive timestamps/read-ahead.
    while len(data) < MAX_PACKET:
        _remaining(sock, deadline)
        char = sock.recv(1)
        if not char:
            raise ValueError('truncated control packet')
        if char == b'\n':
            stamp = now()
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValueError('control packet must be an object')
            return value, stamp
        data.extend(char)
    raise ValueError('control packet too large')


def _document(identity, phase, count):
    if phase not in {'pre', 'post'}:
        raise ValueError('phase must be pre or post')
    return {"schema": "g1-03-host-control-v1", "classification": CLASSIFICATION,
            "privacy": "PRIVATE", "transport": "INDEPENDENT_TCP_CONTROL",
            "phase": phase, "count": count, "unit": "ns", "reference": identity, "exchanges": []}


def serve(bind, port, identity, phase, count=8, timeout=30):
    """Serve one bounded connection; return source-side partial raw evidence."""
    _limits(count, timeout)
    socket.inet_pton(socket.AF_INET, bind)  # literals only: no unbounded DNS lookup
    doc = _document(identity, phase, count)
    doc['source'] = doc.pop('reference')
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((bind, port))
        listener.listen(1)
        print('control-listening', file=sys.stderr, flush=True)
        _remaining(listener, deadline)
        connection, _ = listener.accept()
        with connection:
            for index in range(count):
                request, t2 = _receive(connection, deadline)
                expected = {'run': identity['run'], 'epoch': identity['epoch'], 'phase': phase, 'index': index}
                if any(request.get(key) != value for key, value in expected.items()):
                    raise ValueError('control run/epoch/phase/sequence mismatch')
                if not isinstance(request.get('t1'), int) or isinstance(request['t1'], bool):
                    raise ValueError('invalid t1')
                response = {**expected, 't1': request['t1'], 't2': t2, 'source': identity}
                response['t3'] = now()
                _send(connection, response, deadline)
                doc['exchanges'].append({key: response[key] for key in ('t1', 't2', 't3')})
    return doc


def collect(host, port, identity, phase, count=8, timeout=30):
    """Collect actual socket observations; caller supplies identity, never fixtures."""
    _limits(count, timeout)
    socket.inet_pton(socket.AF_INET, host)  # literals only: no unbounded DNS lookup
    doc = _document(identity, phase, count)
    deadline = time.monotonic() + timeout
    with socket.create_connection((host, port), timeout=timeout) as connection:
        for index in range(count):
            request = {'run': identity['run'], 'epoch': identity['epoch'], 'phase': phase, 'index': index}
            request['t1'] = now()
            _send(connection, request, deadline)
            response, t4 = _receive(connection, deadline)
            if any(response.get(key) != value for key, value in request.items()):
                raise ValueError('control response identity/sequence mismatch')
            if index and response.get('source') != doc['source']:
                raise ValueError('source process changed during capture')
            doc['source'] = response['source']
            doc['exchanges'].append({**{key: response[key] for key in ('t1', 't2', 't3')}, 't4': t4})
    return doc


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer ns')
    return value


def _identity(identity):
    if not isinstance(identity, dict):
        raise ValueError('clock identity missing')
    for key in ('run', 'epoch', 'node', 'time_namespace', 'pid_namespace', 'boot_id'):
        if not isinstance(identity.get(key), str) or not identity[key].strip() or identity[key] == 'UNKNOWN':
            raise ValueError(f'clock identity {key} missing')
    if identity.get('clock_api') != API or _integer(identity.get('resolution_ns'), 'resolution_ns') < 1:
        raise ValueError('CLOCK_MONOTONIC API/resolution invalid')
    if _integer(identity.get('pid'), 'pid') < 1:
        raise ValueError('PID invalid')
    return tuple(identity[key] for key in ('run', 'epoch', 'node', 'time_namespace', 'pid_namespace', 'boot_id', 'clock_api'))


def _control_segment(sample, max_uncertainty_ns):
    """Causal bounds for the actual source receive-to-send segment only.

    For an actual source event between receives t2 and sends t3, causality and
    monotonicity give reference t1 <= a <= t4 and t2 <= b <= t3. Therefore
    b-a is in [t2-t4,t3-t1], even if clock offset/rate varies during exchange.
    No relation between the two clocks' elapsed durations is assumed.
    """
    t1, t2, t3, t4 = [_integer(sample.get(key), key) for key in ('t1', 't2', 't3', 't4')]
    _integer(max_uncertainty_ns, 'max_uncertainty_ns')
    if t4 < t1 or t3 < t2:
        raise ValueError('nonmonotonic control segment')
    uncertainty = (t4-t1+1) // 2
    bounded = uncertainty <= max_uncertainty_ns
    return {'scope': 'CONTROL_SEGMENT_ONLY',
            'status': 'BOUNDED' if bounded else 'UNSAFE',
            'calibration': 'BOUNDED' if bounded else 'UNSAFE',
            'causal_source_segment_ns': [t2, t3],
            'causal_reference_interval_ns': [t1, t4],
            'offset_envelope_over_segment_ns': [t2-t4, t3-t1],
            'uncertainty_half_width_ns': uncertainty,
            'max_uncertainty_ns': max_uncertainty_ns,
            'usable_for_control_segment': bounded,
            'usable_for_training_window': False,
            'mapping_model': 'MONOTONIC_CAUSAL_SEGMENT_NO_RATE_ASSUMPTION'}


def map_control_segment(sample, source_ns, error_ns=0, max_uncertainty_ns=1_000_000):
    """Map an interior source timestamp from supplied four-stamp evidence.

    This pure interval helper does not validate capture identities/provenance;
    use verify_real_capture for real evidence. Timestamp uncertainty must lie
    strictly inside the source segment: equal monotonic readings cannot alone
    establish ordering. No extrapolation to training events is permitted.
    """
    _integer(source_ns, 'source_ns')
    _integer(error_ns, 'error_ns')
    result = _control_segment(sample, max_uncertainty_ns)
    low, high = result['causal_source_segment_ns']
    if not low < source_ns-error_ns <= source_ns+error_ns < high:
        raise ValueError('source timestamp outside control segment interior; no extrapolation')
    t1, t4 = result['causal_reference_interval_ns']
    result['reference_interval_ns'] = [t1, t4]
    result['offset_for_timestamp_ns'] = [source_ns-error_ns-t4, source_ns+error_ns-t1]
    return result


def verify_real_capture(pre, post, audits=(), max_uncertainty_ns=1_000_000):
    """Validate measured evidence separately from G1-02 CPU_SYNTHETIC math.

    Audits bind every training PID's absolute origin to the sampled host clock.
    No user-supplied drift number is accepted as a measured rate bound. A broad
    causal reference envelope covers every source instant between the pre receive
    and post send, without interpolating clock offset or assuming a rate bound.
    BOUNDED means this broad envelope meets the explicit uncertainty budget.
    """
    result = {'status': 'UNSAFE', 'calibration': 'UNSAFE', 'classification': CLASSIFICATION,
              'usable_for_cross_rank': False, 'actual_cross_rank_comparable': False,
              'action': 'UNSAFE_TO_SUBTRACT', 'unit': 'ns', 'reasons': [],
              'assumptions': ['nonnegative one-way delays; symmetry is not assumed',
                              'CLOCK_MONOTONIC remains monotonic in the bound boot/time namespaces'],
              'drift_bound_ppm': 'UNKNOWN', 'timestamp_accuracy_bound_ns': 'UNKNOWN'}
    try:
        _integer(max_uncertainty_ns, 'max_uncertainty_ns')
        identities = None
        phases = []
        for phase, doc in (('pre', pre), ('post', post)):
            if not isinstance(doc, dict) or doc.get('schema') != 'g1-03-host-control-v1' or doc.get('unit') != 'ns' or doc.get('classification') != CLASSIFICATION or doc.get('transport') != 'INDEPENDENT_TCP_CONTROL' or doc.get('phase') != phase:
                raise ValueError('real control evidence classification/transport/phase mismatch')
            pair = tuple(_identity(doc.get(key)) for key in ('reference', 'source'))
            if pair[0][:2] != pair[1][:2] or pair[0][2] == pair[1][2] or pair[0][5] == pair[1][5]:
                raise ValueError('distinct hosts and same run/epoch required')
            if identities is not None and pair != identities:
                raise ValueError('pre/post clock identity changed')
            identities = pair
            _integer(doc.get('count'), 'count')
            samples = doc.get('exchanges')
            if not isinstance(samples, list) or not 1 <= len(samples) <= MAX_SAMPLES or doc.get('count') != len(samples):
                raise ValueError('sample count invalid or incomplete')
            intervals = []
            last_t4 = last_t3 = -1
            for sample in samples:
                t1, t2, t3, t4 = [_integer(sample.get(key), key) for key in ('t1', 't2', 't3', 't4')]
                if t1 < last_t4 or t2 < last_t3 or t4 < t1 or t3 < t2:
                    raise ValueError('nonmonotonic local exchange sequence')
                low, high = t3 - t4, t2 - t1

                intervals.append({**_control_segment(sample, max_uncertainty_ns),
                                  'conditional_constant_offset_envelope_ns': [low, high],
                                  'conditional_envelope_valid': low <= high,
                                  'reference_window_ns': [t1, t4], 'reference_round_trip_ns': t4-t1,
                                  'source_processing_ns': t3-t2, 'nominal_network_rtt_ns': high-low})
                last_t4, last_t3 = t4, t3
            phases.append(intervals)
            result[phase] = intervals
        start, stop = phases[0][-1]['reference_window_ns'][1], phases[1][0]['reference_window_ns'][0]
        if pre['exchanges'][-1]['t3'] > post['exchanges'][0]['t2']:
            raise ValueError('source pre/post phases reversed')
        if start >= stop:
            raise ValueError('pre/post phases overlap or are reversed')
        result['control_segment_scope'] = 'CONTROL_SEGMENT_ONLY; never extrapolate to training window'
        result['bounded_control_segments'] = sum(item['status'] == 'BOUNDED' for phase in phases for item in phase)
        result['reference'] = pre['reference'].copy()
        result['source'] = pre['source'].copy()
        result['validity_reference_ns'] = [start, stop]
        result['validity_status'] = 'CAUSAL_BRACKET_ONLY_NO_OFFSET_INTERPOLATION'
        result['valid_source_ns'] = [pre['exchanges'][-1]['t2'], post['exchanges'][0]['t3']]
        result['valid_source_interval'] = 'OPEN: strict inequalities avoid equal-clock-read ambiguity'
        result['coarse_reference_envelope_ns'] = [pre['exchanges'][-1]['t1'], post['exchanges'][0]['t4']]
        width = result['coarse_reference_envelope_ns'][1] - result['coarse_reference_envelope_ns'][0]
        result['uncertainty_half_width_ns'] = (width + 1) // 2
        result['mapping_model'] = 'MONOTONIC_CAUSAL_BRACKET_NO_DRIFT_ASSUMPTION'
        _integer(max_uncertainty_ns, 'max_uncertainty_ns')
        result['max_uncertainty_ns'] = max_uncertainty_ns
        if not audits:
            raise ValueError('training PID/origin audit binding missing')
        bound_nodes = set()
        pids = set()
        for audit in audits:
            audit = dict(audit)
            for alias, key in (('run_id', 'run'), ('rank_epoch', 'epoch'), ('node_alias', 'node'), ('origin_clock_ns', 'origin_monotonic_ns')):
                if alias in audit:
                    if key in audit and audit[key] != audit[alias]:
                        raise ValueError('conflicting audit identity aliases')
                    audit[key] = audit[alias]
            identity = _identity(audit)
            if identity not in identities:
                raise ValueError('training audit host/time namespace/run/epoch mismatch')
            key = (audit['node'], audit['pid'])
            if key in pids:
                raise ValueError('duplicate training PID audit')
            pids.add(key)
            node_index = identities.index(identity)
            origin = _integer(audit.get('origin_monotonic_ns'), 'origin_monotonic_ns')
            before = pre['exchanges'][-1]['t4' if node_index == 0 else 't2']
            after = post['exchanges'][0]['t1' if node_index == 0 else 't3']
            if not before < origin < after:
                raise ValueError('training origin outside local pre/post window')
            if 'active_until_monotonic_ns' in audit:
                finish = _integer(audit['active_until_monotonic_ns'], 'active_until_monotonic_ns')
                if not origin <= finish < after:
                    raise ValueError('training active window extends outside local pre/post window')
            bound_nodes.add(node_index)
        if bound_nodes != {0, 1}:
            raise ValueError('training origin audits required on both nodes')
        result['training_origin_binding'] = 'OBSERVED'
        result['training_pids_bound'] = len(pids)
        result['reasons'].append('narrow endpoint envelopes are conditional on unverified constant offset during exchanges; no continuous offset/drift calibration established')
        if result['uncertainty_half_width_ns'] > max_uncertainty_ns:
            result['reasons'].append('TOO_WIDE: causal envelope exceeds max_uncertainty_ns')
        else:
            result.update(status='BOUNDED', calibration='BOUNDED', usable_for_cross_rank=True,
                          actual_cross_rank_comparable=True, action='BOUNDED_INTERVAL_COMPARISON_ONLY')
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        result['reasons'].append(str(exc))
    return result


def map_source_time(source_ns, quality, error_ns=0):
    """Map a source instant to its broad causal interval; refuse invalid clocks."""
    _integer(source_ns, 'source_ns')
    _integer(error_ns, 'error_ns')
    if quality.get('training_origin_binding') != 'OBSERVED':
        raise ValueError('training identity binding has not been validated')
    start, stop = quality['valid_source_ns']
    if not start < source_ns - error_ns <= source_ns + error_ns < stop:
        raise ValueError('source timestamp outside causal validity bracket')
    return {'reference_interval_ns': quality['coarse_reference_envelope_ns'][:],
            'status': quality['status'], 'usable_for_cross_rank': quality['usable_for_cross_rank'],
            'mapping_model': quality['mapping_model']}


def _write_private(path, value):
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags, 0o600), 'w') as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(value, output, indent=2, allow_nan=False)
        output.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='role', required=True)
    for role in ('server', 'client'):
        p = sub.add_parser(role)
        p.add_argument('--bind' if role == 'server' else '--host', required=True)
        p.add_argument('--port', type=int, required=True)
        for key in ('run', 'epoch', 'node', 'phase'):
            p.add_argument('--' + key, required=True, **({'choices': ('pre', 'post')} if key == 'phase' else {}))
        p.add_argument('--count', type=int, default=8)
        p.add_argument('--timeout', type=float, default=30)
        p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('verify')
    for key in ('pre', 'post', 'audits', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--max-uncertainty-ns', type=int, default=1_000_000)
    args = parser.parse_args()
    try:
        if args.role == 'verify':
            read = lambda path: json.loads(path.read_text())
            result = verify_real_capture(read(args.pre), read(args.post), read(args.audits), args.max_uncertainty_ns)
        else:
            identity = metadata(args.run, args.epoch, args.node)
            result = (serve if args.role == 'server' else collect)(args.bind if args.role == 'server' else args.host, args.port, identity, args.phase, args.count, args.timeout)
        _write_private(args.output, result)
        return 1 if result.get('status') == 'UNSAFE' else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'control collection failed: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
