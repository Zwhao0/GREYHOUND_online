"""CPU replay of frozen real evidence; does not rerun or simulate GPU capture."""
import hashlib
import json
from pathlib import Path
import unittest
from tools.g2_01_locate import locate
from tools.g2_01_score import aggregate

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence'
def read(name):return json.loads((EVIDENCE/f'g2-01-{name}.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


class PublicEvidence(unittest.TestCase):
    def test_frozen_inputs_sources_and_blind_replay(self):
        frozen=read('freeze')
        for key,name in [('baseline','healthy'),('observed','observed'),('predictions','predictions'),('registration','registration')]:
            self.assertEqual(frozen[key],sha(EVIDENCE/f'g2-01-{name}.json'))
        for name,digest in read('registration')['source_sha256'].items():
            self.assertEqual(sha(ROOT/'tools'/name),digest)
        prediction=read('predictions');replay=locate(read('observed'),read('healthy'))
        for key in replay:self.assertEqual(prediction[key],replay[key])
        self.assertEqual(prediction['input_sha256']['observed'],frozen['observed'])

    def test_revealed_window_aggregation_and_raw_stop_rule(self):
        predictions={(r['comm_hash'],r['function'],r['seq_num']):r for r in read('predictions')['instances']}
        score=read('score');windows=read('evaluation-map')['windows']
        hits=unknown=false=0
        self.assertEqual(len(windows),16)
        for window in windows:
            rows=[predictions[(k['comm_hash'],k['function'],k['seq_num'])] for k in window['instances']]
            result=aggregate(rows)
            published=next(r for r in score['episodes' if window['kind']=='INJECTED' else 'healthy_windows'] if r['step']==window['step'])
            for key,value in result.items():self.assertEqual(value,published[key])
            if window['kind']=='INJECTED':
                hits+=result['rank']==window['truth_rank'] and result['status']=='ROOT_CANDIDATE'
                unknown+=result['status']=='UNKNOWN'
            else:false+=result['status']=='ROOT_CANDIDATE'
        self.assertEqual((hits,unknown,false),(score['top1_correct'],score['injection_unknown'],score['healthy_false_positives']))
        self.assertEqual((hits,unknown,false),(3,0,6))
        self.assertTrue(all(19_000_000<=v<=100_000_000 for v in score['actual_sleep_ns']))
        self.assertEqual(score['conclusion'],'NO_GO_FOR_CURRENT_SIGNAL')


if __name__=='__main__':unittest.main()
