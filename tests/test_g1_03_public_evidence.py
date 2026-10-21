"""Independent CPU consistency checks on redacted REAL G1-03 evidence."""
import json
import statistics
import unittest
from pathlib import Path

REPORT=Path(__file__).resolve().parents[1]/'docs/evidence/g1-03-summary.json'


class PublicRealEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(REPORT.read_text())

    def test_real_exit_identity_and_scoped_counts(self):
        d=self.data
        self.assertEqual(d['candidate_status'],'PARTIAL')
        self.assertEqual(d['matching_summary']['expected_ranks'],4)
        self.assertEqual(d['matching_summary']['matched'],70)
        self.assertEqual({r['global_rank'] for r in d['ranks']},{0,1,2,3})
        for exit in d['resource_exit']:
            self.assertEqual(exit['task_processes_remaining'],0)
            self.assertEqual(exit['launcher_exits'],{'baseline':0,'plugin':0})
        for rank in d['ranks']:
            for cls,telemetry in rank['collector_audit']['classes'].items():
                c=telemetry['counters']
                self.assertEqual(c['callback_attempted'],sum(c[k] for k in ('pool_accepted','known_pool_drop','parent_rejected','guard_rejected')))
                self.assertEqual(c['exported'],rank['event_classes'][cls]['observed_begin_count'])
                self.assertEqual(c['exported'],rank['event_classes'][cls]['paired_count'])
                self.assertEqual(c['overwritten'],'UNKNOWN')
            self.assertEqual(rank['end_to_end_loss'],'UNKNOWN')

    def test_performance_recomputed_from_real_arrays_is_not_sla(self):
        perf=self.data['performance']
        self.assertEqual(perf['overhead_sla'],'NOT_ESTABLISHED')
        for rank in perf['ranks']:
            for mode in ('baseline','plugin'):
                data=rank[mode];values=sorted(data['gpu_step_ms'])
                self.assertEqual(len(values),30)
                self.assertAlmostEqual(statistics.median(values),data['gpu_p50_ms'])
                pos=(len(values)-1)*0.95;lo=int(pos)
                self.assertAlmostEqual(values[lo]+(values[lo+1]-values[lo])*(pos-lo),data['gpu_p95_ms'])
            self.assertAlmostEqual((rank['plugin']['gpu_p50_ms']/rank['baseline']['gpu_p50_ms']-1)*100,rank['p50_change_percent'])

    def test_real_clock_segments_bound_only_their_measured_intervals(self):
        d=self.data;quality=d['host_clock']
        self.assertEqual(quality['status'],'UNSAFE')
        self.assertFalse(quality['usable_for_cross_rank'])
        self.assertEqual(quality['drift_bound_ppm'],'UNKNOWN')
        self.assertGreater(quality['uncertainty_half_width_ns'],quality['max_uncertainty_ns'])
        for phase in ('pre','post'):
            self.assertEqual(len(d['raw_four_stamps_ns'][phase]),8)
            for stamps,bound in zip(d['raw_four_stamps_ns'][phase],quality[phase]):
                a,b,c,e=[stamps[k] for k in ('t1','t2','t3','t4')]
                self.assertEqual(bound['causal_reference_interval_ns'],[a,e])
                self.assertEqual(bound['causal_source_segment_ns'],[b,c])
                self.assertEqual(bound['offset_envelope_over_segment_ns'],[b-e,c-a])
                self.assertEqual(bound['uncertainty_half_width_ns'],(e-a+1)//2)
                self.assertFalse(bound['usable_for_training_window'])
                self.assertEqual(bound['status'],'BOUNDED')
        self.assertFalse(d['gpu_clock']['usable_for_cross_rank'])


if __name__=='__main__':unittest.main()
