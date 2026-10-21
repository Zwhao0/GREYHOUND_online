"""CPU synthetic fixtures only: no GPU, injection efficacy or precision claim."""
import copy
import unittest

from tools.g2_01_locate import DELAY_MARGIN_NS, locate


MS = 1_000_000


def capture(role='OBSERVED', starts=None):
    starts = starts or [[100 * MS, 100 * MS + 1000] for _ in range(4)]
    return dict(schema='g2-01-host-intervals-v1', role=role,
                run_id='healthy' if role == 'HEALTHY_BASELINE' else 'observed',
                rank_epoch='epoch', reference_clock='audited-reference', unit='ns',
                expected_ranks=[0, 1, 2, 3],
                quality=dict(status='BOUNDED', complete=True, dropped=0, truncated=False),
                comparability=dict(workload='dense-ddp', configuration='fixed', rank_mapping='same-devices'),
                instances=[dict(comm_hash='world', function='AllReduce', seq_num=10,
                                count=1024, datatype='float32', algorithm='Ring',
                                protocol='Simple', n_channels=4, status='MATCHED',
                                ranks=[dict(rank=r, status='BOUNDED', start=s)
                                       for r, s in enumerate(starts)])])


def late(rank=2, delay=20 * MS):
    observed = capture()
    observed['instances'][0]['ranks'][rank]['start'] = [100 * MS + delay, 100 * MS + delay + 1000]
    return observed


def decision(observed=None, baseline=None):
    return locate(observed or late(), baseline or capture('HEALTHY_BASELINE'))['instances'][0]


class G201BlindLocatorTests(unittest.TestCase):
    def test_strict_late_arrival_is_candidate_with_same_rank_healthy_evidence(self):
        result = decision()
        self.assertEqual((result['status'], result['rank']), ('ROOT_CANDIDATE', 2))
        self.assertEqual(result['evidence']['strict_later_than'], [0, 1, 3])
        self.assertGreater(result['evidence']['excess_lower_ns'], DELAY_MARGIN_NS)

    def test_long_waiter_duration_does_not_become_root(self):
        observed = late(3)
        for row in observed['instances'][0]['ranks']:
            # Early waiter has the longest Host interval; late rank is shortest.
            duration = 100 * MS if row['rank'] == 0 else MS
            row['end'] = [row['start'][1] + duration, row['start'][1] + duration + 1000]
        self.assertEqual(decision(observed)['rank'], 3)

    def test_missing_and_incomparable_baseline_remain_unknown(self):
        result = locate(late())['instances'][0]
        self.assertEqual(result['reasons'], ['BASELINE_UNAVAILABLE'])
        for field in ('workload', 'configuration', 'rank_mapping'):
            baseline = capture('HEALTHY_BASELINE')
            baseline['comparability'][field] = 'different'
            result = decision(baseline=baseline)
            self.assertEqual(result['reasons'], ['BASELINE_UNAVAILABLE'])
        for field, value in [('datatype', 'float16'), ('algorithm', 'Tree'), ('count', 2048)]:
            baseline = capture('HEALTHY_BASELINE')
            baseline['instances'][0][field] = value
            self.assertEqual(decision(baseline=baseline)['reasons'], ['BASELINE_UNAVAILABLE'])

    def test_same_run_baseline_is_rejected_and_other_rank_baseline_is_not_substituted(self):
        baseline = capture('HEALTHY_BASELINE')
        baseline['run_id'] = 'observed'
        self.assertEqual(decision(baseline=baseline)['reasons'], ['BASELINE_UNAVAILABLE'])
        baseline = capture('HEALTHY_BASELINE')
        baseline['instances'][0]['ranks'][2]['start'] = [115 * MS, 115 * MS + 1000]
        result = decision(baseline=baseline)
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertGreater(result['evidence']['healthy_same_rank_max_upper_ns'], 14 * MS)

    def test_overlap_touching_or_joint_delay_cannot_be_ordered(self):
        for interval in ([100 * MS, 122 * MS], [100 * MS + 1000, 122 * MS]):
            observed = late()
            observed['instances'][0]['ranks'][2]['start'] = interval
            self.assertEqual(decision(observed)['reasons'], ['OVERLAP_OR_NO_STRICT_LATEST'])
        observed = late()
        observed['instances'][0]['ranks'][3]['start'] = [120 * MS, 120 * MS + 1000]
        self.assertEqual(decision(observed)['status'], 'UNKNOWN')

    def test_healthy_or_common_shift_does_not_create_candidate(self):
        observed = capture()
        for row in observed['instances'][0]['ranks']:
            row['start'] = [x + 1000 * MS for x in row['start']]
        self.assertEqual(decision(observed)['status'], 'UNKNOWN')
        self.assertEqual(decision(late(delay=3 * MS))['status'], 'UNKNOWN')

    def test_exact_margin_is_not_sufficient(self):
        # Baseline upper lag=1000ns and observed lower lag=delay-1000ns.
        result = decision(late(delay=DELAY_MARGIN_NS + 2000))
        self.assertEqual(result['evidence']['excess_lower_ns'], DELAY_MARGIN_NS)
        self.assertEqual(result['status'], 'UNKNOWN')

    def test_missing_duplicate_unmatched_or_bad_row_quality_fails_closed(self):
        for mutation in ('missing', 'duplicate', 'unmatched', 'unsafe', 'reversed'):
            observed = late()
            instance = observed['instances'][0]
            if mutation == 'missing':
                instance['ranks'].pop()
            elif mutation == 'duplicate':
                instance['ranks'][3]['rank'] = 2
            elif mutation == 'unmatched':
                instance['status'] = 'MISSING_RANK'
            elif mutation == 'unsafe':
                instance['ranks'][0]['status'] = 'UNSAFE_TO_SUBTRACT'
            else:
                instance['ranks'][0]['start'] = [2, 1]
            self.assertEqual(decision(observed)['status'], 'UNKNOWN', mutation)
        observed = late()
        observed['instances'].append(copy.deepcopy(observed['instances'][0]))
        result = locate(observed, capture('HEALTHY_BASELINE'))
        self.assertTrue(all(r['reasons'] == ['DUPLICATE_INSTANCE'] for r in result['instances']))

    def test_bad_document_quality_and_extra_truth_fields_are_rejected(self):
        for key, value in [('status', 'UNSAFE_TO_SUBTRACT'), ('complete', False),
                           ('dropped', 1), ('truncated', True)]:
            observed = late()
            observed['quality'][key] = value
            self.assertEqual(locate(observed, capture('HEALTHY_BASELINE'))['reasons'], ['CAPTURE_QUALITY'])
        observed = late()
        observed['episode'] = 1
        self.assertEqual(locate(observed, capture('HEALTHY_BASELINE'))['reasons'], ['UNSUPPORTED_INPUT_FIELDS'])
        observed = late()
        observed['instances'][0]['ranks'][2]['injected'] = True
        self.assertEqual(decision(observed)['reasons'], ['INVALID_RANK_FIELDS'])

    def test_baseline_quality_is_not_silently_filtered(self):
        baseline = capture('HEALTHY_BASELINE')
        invalid = copy.deepcopy(baseline['instances'][0])
        invalid['seq_num'] += 1
        invalid['ranks'].pop()
        baseline['instances'].append(invalid)
        self.assertEqual(decision(baseline=baseline)['reasons'], ['BASELINE_QUALITY'])

    def test_each_instance_is_processed_without_episode_or_sequence_ranking(self):
        observed = late(1)
        healthy = copy.deepcopy(capture()['instances'][0])
        healthy['seq_num'] = 500
        observed['instances'].insert(0, healthy)
        result = locate(observed, capture('HEALTHY_BASELINE'))
        self.assertEqual([r['status'] for r in result['instances']], ['UNKNOWN', 'ROOT_CANDIDATE'])
        self.assertEqual(result['instances'][1]['rank'], 1)


if __name__ == '__main__':
    unittest.main()
