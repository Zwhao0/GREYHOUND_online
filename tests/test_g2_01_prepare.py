"""CPU synthetic adapter records only; no capture/truth/GPU files read."""
import unittest
from tools.g2_01_prepare import PINNED_LIBRARIES, analysis_scope, comparability


def inputs():
    result = []
    for r in range(4):
        rank = dict(global_rank=r, local_rank=r % 2, node_alias='node-a' if r < 2 else 'node-b')
        raw = dict(run_id='run', rank_epoch='epoch')
        record = dict(run_id='run', rank_epoch='epoch', rank=r, local_rank=r % 2,
                      node_alias=rank['node_alias'], world_size=4, mode='multinode',
                      warmup=5, steps=40, batch=32, width=1024, seed=20261020,
                      torch='2.14.1+cu130', cuda_build='13.0', nccl_python_version=[2,30,7],
                      script_sha256='a'*64, gpu_uuid_private='private-test-uuid-'+str(r),
                      gpu_name='H800', device=r % 2,
                      loaded_libraries=[dict(path='/synthetic/'+k,sha256=v) for k,v in PINNED_LIBRARIES.items()],
                      nccl_config={k:'UNSET' for k in ('NCCL_MIN_NCHANNELS','NCCL_MAX_NCHANNELS',
                                   'NCCL_MIN_CTAS','NCCL_MAX_CTAS','NCCL_NVLS_NCHANNELS')})
        record['nccl_config']['NCCL_PROFILE_EVENT_MASK'] = '66'
        result.append((rank,raw,{},record))
    return result


class G201PrepareTests(unittest.TestCase):
    def test_operation_scope_preserves_bad_allreduce_and_excludes_startup(self):
        matches = dict(instances=[dict(function='Broadcast',status='UNKNOWN'),
                                  dict(function='AllReduce',status='MATCHED'),
                                  dict(function='AllReduce',status='MISSING_RANK')])
        selected, excluded = analysis_scope(matches)
        self.assertEqual(len(selected),2)
        self.assertEqual(selected[-1]['status'],'MISSING_RANK')
        self.assertEqual(excluded,{'Broadcast':1})

    def test_actual_signatures_are_stable_opaque_and_change_with_configuration(self):
        original = comparability(inputs())
        self.assertNotIn('private-test-uuid',str(original))
        changed = inputs()
        for _,_,_,record in changed:
            record['nccl_config']['NCCL_MAX_CTAS'] = '16'
        self.assertNotEqual(original['configuration'],comparability(changed)['configuration'])
        changed = inputs()
        changed[0][3]['gpu_uuid_private'] = 'another-physical-device'
        self.assertNotEqual(original['rank_mapping'],comparability(changed)['rank_mapping'])

    def test_workload_script_runtime_library_and_mapping_mismatch_rejected(self):
        for key,value in [('warmup',4),('steps',30),('script_sha256','bad'),
                          ('torch','different'),('gpu_uuid_private','UNKNOWN'),('local_rank',9)]:
            records=inputs()
            records[0][3][key]=value
            with self.assertRaises(ValueError,msg=key):
                comparability(records)
        records=inputs()
        records[0][3]['script_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'per-rank'):
            comparability(records)
        records=inputs()
        records[0][3]['loaded_libraries'][0]['sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'DSO'):
            comparability(records)
        records=inputs()
        records[1][3]['gpu_uuid_private']=records[0][3]['gpu_uuid_private']
        with self.assertRaisesRegex(ValueError,'nonunique'):
            comparability(records)


if __name__=='__main__':
    unittest.main()
