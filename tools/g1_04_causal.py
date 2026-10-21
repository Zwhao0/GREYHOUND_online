#!/usr/bin/env python3
"""CPU-only strict causal Host envelopes. No rate assumption or Rank scoring."""
from bisect import bisect_left, bisect_right
from tools.g1_03_host_clock import _identity, _integer

UNSAFE='UNSAFE_TO_SUBTRACT'

def normalized(audit):
    out=dict(audit)
    for old,new in [('run_id','run'),('rank_epoch','epoch'),('node_alias','node')]:
        if old in out:
            if new in out and out[new]!=out[old]:raise ValueError('conflicting identity aliases')
            out[new]=out[old]
    return out

def validate_capture(client, server, audits):
    q=dict(status=UNSAFE,reasons=[],unit='ns',mapping_model='STRICT_MONOTONIC_CAUSAL_NO_RATE_ASSUMPTION')
    try:
        for doc in (client,server):
            if any(doc.get(k)!=v for k,v in dict(schema='g1-04-host-control-v1',classification='REAL_HOST_CONTROL',transport='INDEPENDENT_TCP_CONTROL',phase='continuous',unit='ns').items()):raise ValueError('control schema/classification/transport/unit mismatch')
            if doc.get('complete') is not True:raise ValueError('incomplete control capture')
            _integer(doc.get('count'),'count')
            samples=doc.get('exchanges')
            if not isinstance(samples,list) or not 1<=len(samples)<=120000 or doc.get('count')!=len(samples):raise ValueError('control data lost/count mismatch')
        ref,src=[_identity(client.get(k)) for k in ('reference','source')]
        if ref[:2]!=src[:2] or ref[2]==src[2] or ref[5]==src[5]:raise ValueError('same run/epoch and distinct hosts required')
        if server.get('source')!=client['source']:raise ValueError('source PID/identity changed')
        if len(server['exchanges'])!=len(client['exchanges']):raise ValueError('server/client control data lost')
        previous=(-1,-1)
        for i,(a,b) in enumerate(zip(client['exchanges'],server['exchanges'])):
            if type(a.get('index')) is not int or type(b.get('index')) is not int or a.get('index')!=i or b.get('index')!=i:raise ValueError('control index missing/out of order')
            if b!={k:a[k] for k in ('index','t1','t2','t3')}:raise ValueError('server/client control mismatch')
            t1,t2,t3,t4=[_integer(a.get(k),k) for k in ('t1','t2','t3','t4')]
            if t1<previous[0] or t2<previous[1] or t4<t1 or t3<t2:raise ValueError('local clock rollback/nonmonotonic sequence')
            previous=(t4,t3)
        bound={}
        for raw in audits:
            a=normalized(raw);identity=_identity(a)
            if identity not in (ref,src):raise ValueError('training PID clock namespace/boot/run/epoch mismatch')
            origin=_integer(a.get('origin_monotonic_ns'),'origin');finish=_integer(a.get('active_until_monotonic_ns'),'active until')
            if origin>finish:raise ValueError('training local time rollback')
            if _integer(a.get('origin_mapping_error_ns'),'origin mapping error') < 1:raise ValueError('origin mapping error bound missing')
            if a.get('unit','ns')!='ns':raise ValueError('training timestamp unit mismatch')
            key=(a['node'],a['pid'])
            if key in bound:raise ValueError('duplicate training PID')
            bound[key]=a
        if {k[0] for k in bound}!={ref[2],src[2]}:raise ValueError('both training nodes must be audited')
        q.update(status='BOUNDED',client=client,audits=bound,
                 t2=[x['t2'] for x in client['exchanges']],t3=[x['t3'] for x in client['exchanges']])
    except (ValueError,TypeError,KeyError,AttributeError) as exc:q['reasons'].append(str(exc))
    return q

def map_event(quality,audit,source_ns,error_ns=4000,budget_ns=1000000):
    r=dict(status=UNSAFE,reference_interval_ns=None,half_width_ns=None,evidence_indices=[],reasons=[],unit='ns',coverage=False)
    try:
        if quality.get('status')!='BOUNDED':raise ValueError('invalid control evidence: '+str(quality.get('reasons')))
        _integer(source_ns,'event');_integer(error_ns,'event error');_integer(budget_ns,'budget')
        a=normalized(audit);key=(a['node'],a['pid'])
        if quality['audits'].get(key)!=a:raise ValueError('training PID/origin identity changed')
        if error_ns<a['origin_mapping_error_ns']:raise ValueError('unsupported smaller representation error')
        r['reference_clock']=list(_identity(quality['client']['reference']))
        lo,hi=source_ns-error_ns,source_ns+error_ns
        if not a['origin_monotonic_ns']<=lo<=hi<=a['active_until_monotonic_ns']:raise ValueError('event outside audited active window')
        doc=quality['client']
        if a['node']==doc['reference']['node']:
            interval=[lo,hi];indices=[]
        else:
            # Receive supports lower bound; send supports upper bound. Strict
            # inequalities cover the complete event representation interval.
            left=bisect_left(quality['t2'],lo)-1
            right=bisect_right(quality['t3'],hi)
            if left<0 or right>=len(doc['exchanges']):raise ValueError('NO_SAMPLE_COVERAGE: missing causal side')
            interval=[doc['exchanges'][left]['t1'],doc['exchanges'][right]['t4']]
            indices=sorted(set((left,right)))
        if interval[0]>interval[1]:raise ValueError('inconsistent causal envelope')
        half=(interval[1]-interval[0]+1)//2
        r.update(reference_interval_ns=interval,half_width_ns=half,evidence_indices=indices,coverage=True)
        if half>budget_ns:raise ValueError('TOO_WIDE: causal envelope exceeds budget')
        r['status']='BOUNDED'
    except (ValueError,TypeError,KeyError,AttributeError) as exc:r['reasons'].append(str(exc))
    return r

def compare_intervals(left,right):
    if left.get('status')!='BOUNDED' or right.get('status')!='BOUNDED':return 'OVERLAP_OR_UNKNOWN'
    if not left.get('reference_clock') or left.get('reference_clock')!=right.get('reference_clock'):return 'OVERLAP_OR_UNKNOWN'
    if left.get('unit')!='ns' or right.get('unit')!='ns':return 'OVERLAP_OR_UNKNOWN'
    a,b=left.get('reference_interval_ns'),right.get('reference_interval_ns')
    if any(not isinstance(v,(list,tuple)) or len(v)!=2 or any(type(x) is not int or x<0 for x in v) or v[0]>v[1] for v in (a,b)):return 'OVERLAP_OR_UNKNOWN'
    if a[1]<b[0]:return 'BEFORE'
    if b[1]<a[0]:return 'AFTER'
    return 'OVERLAP_OR_UNKNOWN'
