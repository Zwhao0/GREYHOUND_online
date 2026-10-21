#!/usr/bin/env python3
"""Independent reveal/scoring. Must run AFTER freeze; never imports locator."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(paths, destination):
    """Exclusive immutable-by-protocol manifest; hash it externally before reveal."""
    record={name:sha(path) for name,path in paths.items()}
    with destination.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    return sha(destination)


def decisions_by_step(observed, predictions, truths):
    if predictions.get('status')!='COMPLETE':
        return {},'PREDICTIONS_INCOMPLETE'
    rows={ (x['comm_hash'],x['function'],x['seq_num']):x for x in predictions['instances'] }
    if len(rows)!=len(predictions['instances']):raise ValueError('duplicate prediction')
    result={}
    for instance in observed['instances']:
        steps=[]
        for rank in instance['ranks']:
            matches=[b['step'] for b in truths[rank['rank']]['step_boundaries']
                     if b['start_monotonic_ns'] <= rank['source_ns'] <= b['end_monotonic_ns']]
            if len(matches)!=1: break
            steps.append(matches[0])
        if len(steps)!=4 or len(set(steps))!=1:continue
        key=(instance['comm_hash'],instance['function'],instance['seq_num'])
        result.setdefault(steps[0],[]).append(rows[key])
    return result,None


def aggregate(rows):
    candidates={x['rank'] for x in rows if x['status']=='ROOT_CANDIDATE'}
    return dict(status='ROOT_CANDIDATE' if len(candidates)==1 else 'UNKNOWN',
                rank=next(iter(candidates)) if len(candidates)==1 else None,
                matched_collectives=len(rows),candidate_collectives=sum(x['status']=='ROOT_CANDIDATE' for x in rows))


def score(plan, observed, predictions, truths, healthy_steps):
    """All 8 predeclared episodes count; UNKNOWN is never a hit."""
    episodes=plan['episodes']
    if (len(episodes)!=8 or len({e['step'] for e in episodes})!=8
            or sorted(e['rank'] for e in episodes)!=[0,0,1,1,2,2,3,3]
            or any(type(e['step']) is not int or not 0<=e['step']<40 or e['delay_s']!=.020 for e in episodes)):
        raise ValueError('invalid preregistered episodes')
    if (len(healthy_steps)!=8 or len(set(healthy_steps))!=8
            or any(type(s) is not int or not 0<=s<40 for s in healthy_steps)
            or set(healthy_steps)&{e['step'] for e in episodes}):
        raise ValueError('exactly eight distinct non-injected healthy windows required')
    actual=[]
    for rank,doc in truths.items():
        if doc['rank']!=rank or doc['steps']!=40 or doc['warmup']!=5 or doc['plan_nonce']!=plan['nonce']:
            raise ValueError('truth identity mismatch')
        if [b['step'] for b in doc['step_boundaries']]!=list(range(40)):
            raise ValueError('truth boundary loss')
        previous=-1
        for b in doc['step_boundaries']:
            start,end=b['start_monotonic_ns'],b['end_monotonic_ns']
            if type(start) is not int or type(end) is not int or start<previous or end<start:
                raise ValueError('invalid or overlapping local boundaries')
            previous=end
            injection=b.get('injection')
            if injection:
                if not (start <= injection['sleep_start_monotonic_ns'] <= injection['sleep_end_monotonic_ns'] <= end):
                    raise ValueError('sleep outside step')
                actual.append((b['step'],rank,injection))
    expected={(e['step'],e['rank']) for e in plan['episodes']}
    if {(s,r) for s,r,_ in actual}!=expected or len(actual)!=8:raise ValueError('injection truth mismatch')
    effective=all(19_000_000 <= a['sleep_end_monotonic_ns']-a['sleep_start_monotonic_ns'] <=100_000_000 for _,_,a in actual)
    bystep,problem=decisions_by_step(observed,predictions,truths)
    episodes=[]
    for e in plan['episodes']:
        pred=aggregate(bystep.get(e['step'],[]))
        episodes.append(dict(step=e['step'],truth_rank=e['rank'],**pred,correct=pred['status']=='ROOT_CANDIDATE' and pred['rank']==e['rank']))
    healthy=[dict(step=s,**aggregate(bystep.get(s,[]))) for s in healthy_steps]
    hits=sum(x['correct'] for x in episodes);unknown=sum(x['status']=='UNKNOWN' for x in episodes)
    false=sum(x['status']=='ROOT_CANDIDATE' for x in healthy)
    valid=(effective and problem is None and all(x['matched_collectives']>0 for x in episodes+healthy))
    conclusion=('INCONCLUSIVE' if not valid else ('GO' if hits>=7 and false<=1 else 'NO_GO_FOR_CURRENT_SIGNAL'))
    return dict(schema='g2-01-score-v1',classification='GPU_MULTINODE_PILOT',injection_effective=effective,
                episodes=episodes,healthy_windows=healthy,top1_correct=hits,top1_total=8,top1_rate=hits/8,
                injection_unknown=unknown,injection_unknown_rate=unknown/8,healthy_false_positives=false,
                healthy_total=len(healthy),healthy_unknown=sum(x['status']=='UNKNOWN' for x in healthy),
                conclusion=conclusion,gate='G2_NOT_PASSED_PENDING_INDEPENDENT_REVIEW',
                actual_sleep_ns=[a['sleep_end_monotonic_ns']-a['sleep_start_monotonic_ns'] for _,_,a in sorted(actual)],
                scope='8 engineering pilot episodes; UNKNOWN counts as miss; no accuracy or G2 Gate claim')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','registration','observed','predictions','freeze','truth-root','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();frozen=json.loads(a.freeze.read_text())
    for name,path in [('plan',a.plan),('registration',a.registration),('observed',a.observed),('predictions',a.predictions)]:
        if frozen[name]!=sha(path):raise ValueError('freeze hash mismatch: '+name)
    predictions=json.loads(a.predictions.read_text())
    if predictions.get('input_sha256',{}).get('observed')!=sha(a.observed):
        raise ValueError('predictions not bound to observed input')
    reg=json.loads(a.registration.read_text())
    if reg['plan_sha256']!=sha(a.plan):raise ValueError('precommit mismatch')
    truths={}
    for path in a.truth_root.glob('node-*/truth/rank-*.json'):
        doc=json.loads(path.read_text());rank=doc['rank']
        if rank in truths:raise ValueError('duplicate truth')
        truths[rank]=doc
    if set(truths)!={0,1,2,3}:raise ValueError('missing truth')
    result=score(json.loads(a.plan.read_text()),json.loads(a.observed.read_text()),json.loads(a.predictions.read_text()),truths,reg['healthy_steps'])
    result['freeze_sha256']=sha(a.freeze);result['plan_sha256']=sha(a.plan);result['scorer_sha256']=sha(Path(__file__))
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(result['conclusion'])
if __name__=='__main__':main()
