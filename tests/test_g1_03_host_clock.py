"""CPU fixtures and actual loopback only; no GPU or multinode calibration proof."""
import copy
import json
import socket
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path

from tools.g1_03_host_clock import (
    API, CLASSIFICATION, _limits, _write_private, collect, map_control_segment, map_source_time,
    serve, verify_real_capture,
)


def identity(node):
    return {'run': 'run-a', 'epoch': 'epoch-a', 'node': node, 'pid': 100,
            'time_namespace': 'time:[1]', 'pid_namespace': 'pid:[1]',
            'boot_id': 'boot-' + node, 'clock_api': API, 'resolution_ns': 1}


def fixture(phase):
    # Deliberately arbitrary change in offset between phases: do not interpolate.
    sample = dict(t1=100, t2=1000, t3=1002, t4=110) if phase == 'pre' else dict(t1=10000, t2=8000, t3=8004, t4=10020)
    return {'schema': 'g1-03-host-control-v1', 'unit': 'ns', 'classification': CLASSIFICATION, 'transport': 'INDEPENDENT_TCP_CONTROL',
            'phase': phase, 'reference': identity('node0'), 'source': identity('node1'),
            'count': 1, 'exchanges': [sample]}


def audits():
    return [{**identity('node0'), 'pid': 200, 'origin_monotonic_ns': 500},
            {**identity('node1'), 'pid': 201, 'origin_monotonic_ns': 2000}]


class RealHostClockTests(unittest.TestCase):
    def test_coarse_causality_bound_without_drift_model(self):
        result = verify_real_capture(fixture('pre'), fixture('post'), audits(), 100)
        self.assertEqual(result['status'], 'UNSAFE')
        self.assertEqual(result['coarse_reference_envelope_ns'], [100, 10020])
        self.assertEqual(result['uncertainty_half_width_ns'], 4960)
        self.assertEqual(result['valid_source_ns'], [1000, 8004])
        self.assertEqual(result['drift_bound_ppm'], 'UNKNOWN')
        self.assertEqual(map_source_time(3000, result)['reference_interval_ns'], [100, 10020])
        self.assertFalse(result['usable_for_cross_rank'])
        json.dumps(result, allow_nan=False)

    def test_explicit_wide_budget_only_permits_broad_interval(self):
        result = verify_real_capture(fixture('pre'), fixture('post'), audits(), 4960)
        self.assertEqual(result['status'], 'BOUNDED')
        self.assertNotEqual(result['calibration'], 'CALIBRATED')
        self.assertTrue(result['usable_for_cross_rank'])
        for stamp in (999, 1000, 8004, 8005):
            with self.assertRaises(ValueError):
                map_source_time(stamp, result)

    def test_synthetic_interface_is_rejected(self):
        doc = fixture('pre')
        doc['classification'] = 'CPU_SYNTHETIC'
        self.assertFalse(verify_real_capture(doc, fixture('post'), audits())['usable_for_cross_rank'])

    def test_identity_or_origin_changes_fail_closed(self):
        for key, value in (('time_namespace', 'time:[2]'), ('pid_namespace', 'pid:[2]'),
                           ('boot_id', 'reboot'), ('run', 'other'), ('epoch', 'other'),
                           ('clock_api', 'GPU_GLOBALTIMER'), ('origin_monotonic_ns', 999999)):
            with self.subTest(key=key):
                modified = audits()
                modified[1][key] = value
                result = verify_real_capture(fixture('pre'), fixture('post'), modified, 100000)
                self.assertEqual(result['status'], 'UNSAFE')
                self.assertFalse(result['usable_for_cross_rank'])

    def test_missing_audit_does_not_allow_mapping(self):
        result = verify_real_capture(fixture('pre'), fixture('post'), [])
        with self.assertRaises(ValueError):
            map_source_time(2000, result)

    def test_training_audit_aliases(self):
        values = audits()
        for audit in values:
            for old, new in (('run', 'run_id'), ('epoch', 'rank_epoch'), ('node', 'node_alias'), ('origin_monotonic_ns', 'origin_clock_ns')):
                audit[new] = audit.pop(old)
        self.assertEqual(verify_real_capture(fixture('pre'), fixture('post'), values)['training_origin_binding'], 'OBSERVED')

    def test_reversed_or_incomplete_samples_rejected(self):
        for change in ('reversed', 'missing', 'same_host', 'post_namespace'):
            pre, post = fixture('pre'), fixture('post')
            if change == 'reversed': post['exchanges'][0]['t2'] = 900
            elif change == 'missing': pre['count'] = 2
            elif change == 'same_host': pre['source']['boot_id'] = pre['reference']['boot_id']
            else: post['source']['time_namespace'] = 'time:[2]'
            self.assertEqual(verify_real_capture(pre, post, audits(), 100000)['status'], 'UNSAFE')

    def test_limits_and_private_permissions(self):
        for count, timeout in ((0, 1), (33, 1), (True, 1), (1, float('nan')), (1, 121)):
            with self.assertRaises(ValueError):
                _limits(count, timeout)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.json'
            path.write_text('{}')
            path.chmod(0o644)
            _write_private(path, {'test_classification': 'CPU'})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_actual_loopback_exchange_is_bounded_and_four_stamps(self):
        # CPU loopback transport smoke only. Fake identities never prove two hosts.
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        results, errors = [], []
        def worker():
            try: results.append(serve('127.0.0.1', port, identity('node1'), 'pre', 2, 2))
            except Exception as exc: errors.append(exc)
        thread = threading.Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 1
        while True:
            try:
                doc = collect('127.0.0.1', port, identity('node0'), 'pre', 2, 1)
                break
            except ConnectionRefusedError:
                if time.monotonic() > deadline: raise
                time.sleep(.005)
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 1)
        for sample in doc['exchanges']:
            self.assertLessEqual(sample['t1'], sample['t4'])
            self.assertLessEqual(sample['t2'], sample['t3'])
            self.assertEqual(set(sample), {'t1', 't2', 't3', 't4'})

    def test_negative_equal_rate_envelope_does_not_invalidate_causal_bound(self):
        pre = fixture('pre')
        pre['exchanges'][0]['t3'] = 1020
        result = verify_real_capture(pre, fixture('post'), audits(), 10000)
        self.assertFalse(result['pre'][0]['conditional_envelope_valid'])
        self.assertEqual(result['status'], 'BOUNDED')
        self.assertEqual(result['coarse_reference_envelope_ns'], [100, 10020])

    def test_active_window_and_rounding_uncertainty_must_fit(self):
        values = audits()
        values[1]['active_until_monotonic_ns'] = 9000
        self.assertEqual(verify_real_capture(fixture('pre'), fixture('post'), values, 100000)['status'], 'UNSAFE')
        quality = verify_real_capture(fixture('pre'), fixture('post'), audits())
        with self.assertRaises(ValueError):
            map_source_time(1001, quality, error_ns=2)

    def test_control_segment_rate_free_contains_nonlinear_clock_offset(self):
        # Real reference coordinates: send=100, B receive=101, B send=109,
        # receive=110. B advances arbitrarily nonlinearly 1000->1020 across
        # that segment; source/reference elapsed durations need not match.
        sample = dict(t1=100, t2=1000, t3=1020, t4=110)
        for source_ns, simultaneous_reference in ((1001, 102), (1010, 103), (1019, 108)):
            mapped = map_control_segment(sample, source_ns, max_uncertainty_ns=5)
            self.assertEqual(mapped['status'], 'BOUNDED')
            low, high = mapped['reference_interval_ns']
            self.assertLessEqual(low, simultaneous_reference)
            self.assertGreaterEqual(high, simultaneous_reference)
            offset = source_ns-simultaneous_reference
            low, high = mapped['offset_envelope_over_segment_ns']
            self.assertLessEqual(low, offset)
            self.assertGreaterEqual(high, offset)
        self.assertEqual(mapped['offset_envelope_over_segment_ns'], [890, 920])
        self.assertEqual(mapped['uncertainty_half_width_ns'], 5)

    def test_control_segment_mapping_rejects_extrapolation_and_wide_budget(self):
        sample = dict(t1=100, t2=1000, t3=1020, t4=111)
        for source_ns, error in ((999, 0), (1000, 0), (1020, 0), (1021, 0), (1001, 2)):
            with self.assertRaises(ValueError):
                map_control_segment(sample, source_ns, error)
        mapped = map_control_segment(sample, 1010, max_uncertainty_ns=5)
        self.assertEqual(mapped['status'], 'UNSAFE')
        self.assertEqual(mapped['uncertainty_half_width_ns'], 6)
        self.assertFalse(mapped['usable_for_training_window'])

    def test_real_verifier_control_segment_scope_does_not_relax_training(self):
        result = verify_real_capture(fixture('pre'), fixture('post'), audits(), 10)
        self.assertEqual(result['bounded_control_segments'], 2)
        for phase in ('pre', 'post'):
            segment = result[phase][0]
            self.assertEqual(segment['status'], 'BOUNDED')
            self.assertEqual(segment['scope'], 'CONTROL_SEGMENT_ONLY')
            self.assertTrue(segment['usable_for_control_segment'])
            self.assertFalse(segment['usable_for_training_window'])
        self.assertEqual(result['status'], 'UNSAFE')
        self.assertFalse(result['usable_for_cross_rank'])

    def test_dns_names_rejected_before_connect(self):
        with self.assertRaises(OSError):
            collect('example.invalid', 9999, identity('node0'), 'pre', 1, .02)

    def test_server_without_peer_times_out(self):
        with self.assertRaises((TimeoutError, socket.timeout)):
            serve('127.0.0.1', 0, identity('node1'), 'pre', 1, .02)


if __name__ == '__main__':
    unittest.main()
