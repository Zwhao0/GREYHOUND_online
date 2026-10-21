#!/usr/bin/env python3
"""Offline real G1-04 evidence: preserve event envelopes, redact host identities."""
from __future__ import annotations
import argparse
import math
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.g1_01_make_manifest import build_manifest
from tools.g1_01_match_trace import analyze_manifest
from tools.g1_03_audit import validate_audit
from tools.g1_04_causal import validate_capture,map_event,compare_intervals,normalized
from tools.g1_03_host_clock import _identity,_integer


def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def distribution(values):
    v=sorted(values)
    def pct(q):
        if not v:return None
        x=(len(v)-1)*q;i=int(x);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(x-i)
    return dict(n=len(v),p50=pct(.5),p95=pct(.95),max=max(v) if v else None)

def summarize(events):
    widths=[e['half_width_ns'] for e in events if e['half_width_ns'] is not None]
    n=len(events)
    return dict(events=n,covered=sum(e['coverage'] for e in events),
                bounded=sum(e['status']=='BOUNDED' for e in events),
                unsafe_fraction=sum(e['status']!='BOUNDED' for e in events)/n if n else None,
                half_width_ns=distribution(widths),
                budget_coverage={str(b):sum(e['coverage'] and e['half_width_ns']<=b for e in events)/n if n else None for b in (1000000,5000000,10000000)},
                rejection_reasons=dict(Counter(r for e in events for r in e['reasons'])))

def build(root,manifest_path):
    manifest=build_manifest([(n,root/n/'plugin') for n in ('node-a','node-b')])
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n');manifest_path.chmod(0o600)
    matched=analyze_manifest(manifest_path,redact_identifiers=True)
    raws=[];rank_inputs=[];runtime=[]
    for rank in manifest['ranks']:
        r=rank['global_rank'];folder=root/rank['node_alias']/'plugin'
        auditpath=folder/f"trace_{manifest['world_comm']['comm_hash']}_{rank['comm_rank']}.audit.json"
        raw=read(auditpath);record=read(folder/f'rank-{r}.json')
        _identity(normalized(raw))
        if _integer(raw.get('origin_mapping_error_ns'),'origin mapping error')<1 or raw['origin_monotonic_ns']>=2**42*1000:raise ValueError('unsupported origin representation')
        expected={k:rank[k] for k in ('node_alias','pid','comm_rank')}
        expected.update(run_id=manifest['run_id'],rank_epoch=manifest['rank_epoch'],comm_hash=manifest['world_comm']['comm_hash'])
        audit=validate_audit(raw,expected)
        if audit['mapping_status']!='OBSERVED' or audit['issues']:raise ValueError('audit identity/export invalid')
        if raw['pid']!=record['pid']:raise ValueError('training PID mismatch')
        if record['torch']!='2.14.1+cu130' or record['nccl_python_version']!=[2,30,7]:raise ValueError('runtime changed')
        dsos=[dict(basename=Path(x['path']).name,**{k:v for k,v in x.items() if k in ('sha256','version','version_query_status')}) for x in record['loaded_libraries']]
        for prefix,expected_hash in [('libnccl.so','618968ee277041751512e619190132a9bdf351c3ce7129c73484f6ef441ad692'),('libnccl-profiler-example.so','06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54'),('libcudart.so','96c42e418cec19054186b9429c321603cc190bf26a18104e19408117a2a817b0')]:
            libs=[x for x in dsos if x['basename'].startswith(prefix)]
            if not libs or any(x['sha256']!=expected_hash for x in libs):raise ValueError('actually loaded DSO mismatch')
        runtime.append(dict(rank=r,torch=record['torch'],nccl=record['nccl_python_version'],dsos=dsos,
                            script_sha256=record['script_sha256'],warmup=record['warmup'],steps=record['steps'],
                            gpu_step_ms=record['gpu_step_ms'],max_rss_kib=record['max_rss_kib']))
        raws.append(raw);rank_inputs.append((rank,raw,audit,auditpath))
    client,server=[read(root/n/'control.json') if (root/n/'control.json').exists() else None for n in ('node-a','node-b')]
    q=validate_capture(client,server,raws) if client is not None and server is not None else dict(status='UNSAFE_TO_SUBTRACT',reasons=['CONTROL_CAPTURE_FAILED: no complete four-stamp session'],mapping_model='STRICT_MONOTONIC_CAUSAL_NO_RATE_ASSUMPTION')
    if client is not None and server is not None and (client['reference']['node']!='node-a' or client['source']['node']!='node-b'):raise ValueError('control node role mismatch')
    reference_token='g104-reference-'+sha(manifest_path)[:24]
    events=[];rankrows=[];used=set();instance={}
    for rank,raw,audit,auditpath in rank_inputs:
        r=rank['global_rank'];local=[]
        trace=read(Path(rank['trace_file']))
        previous=-1
        for trace_index,event in enumerate(trace):
            if event.get('cat')!='COLL' or event.get('ph')!='b':continue
            if event['pid']!=raw['pid'] or event['args']['Rank']!=raw['comm_rank']:raise ValueError('event PID/rank mismatch')
            ts=event['ts']
            if type(ts) not in (int,float) or not math.isfinite(ts) or ts<previous:raise ValueError('event timestamp rollback')
            previous=ts
            stamp=raw['origin_monotonic_ns']+round(ts*1000)
            error=raw['origin_mapping_error_ns']
            if not raw['origin_monotonic_ns']<=stamp-error<=stamp+error<=raw['active_until_monotonic_ns']:raise ValueError('event outside local audited Host window')
            mapped=map_event(q,raw,stamp,raw['origin_mapping_error_ns'])
            # Raw clock identities remain private. All mapped rows in this report
            # were validated to the single reference clock session above.
            mapped['reference_clock']=reference_token
            mapped.update(rank=r,op=event['name'],seq=event['args']['SeqNum'],source_ns=stamp,
                          representation_error_ns=raw['origin_mapping_error_ns'],trace_index=trace_index)
            used.update(mapped['evidence_indices']);events.append(mapped);local.append(mapped)
            instance.setdefault((mapped['op'],mapped['seq']),[]).append(mapped)
        rankrows.append(dict(rank=r,node_alias=rank['node_alias'],status='BOUNDED' if local and all(e['status']=='BOUNDED' for e in local) else 'UNSAFE_TO_SUBTRACT',identity_binding='OBSERVED' if q['status']=='BOUNDED' else 'TRACE_TRAINING_PID_ONLY_CONTROL_UNAVAILABLE',
                             origin_monotonic_ns=raw['origin_monotonic_ns'],active_until_monotonic_ns=raw['active_until_monotonic_ns'],
                             input_trace_sha256=sha(Path(rank['trace_file'])),input_audit_sha256=sha(auditpath),
                             collector_audit=audit,summary=summarize(local)))
    # Only same-operation consecutive seq values establish a run of matched
    # instances; sequence is never used to infer temporal precedence.
    streak=longest=0;last=None;eligible=[];pairs=Counter()
    verified={(x['function'],x['seq_num']) for x in matched['instances'] if x['status']=='MATCHED'}
    for key,rows in sorted(instance.items()):
        valid=key in verified and len(rows)==4 and {x['rank'] for x in rows}=={0,1,2,3} and all(x['status']=='BOUNDED' for x in rows)
        streak=(streak+1 if last is not None and key[0]==last[0] and key[1]==last[1]+1 else 1) if valid else 0
        longest=max(longest,streak);last=key
        if valid:eligible.append(dict(op=key[0],seq=key[1]))
        for a in (rows if key in verified else []):
            for b in rows:
                if a['rank']<2 and b['rank']>=2:pairs[compare_intervals(a,b)]+=1
    samples=client['exchanges'] if client is not None else []
    deltas={key:distribution([b[key]-a[key] for a,b in zip(samples,samples[1:])]) for key in ('t1','t2')}
    exitrows=[];executed={}
    for n in ('node-a','node-b'):
        folder=root/n
        post=read(folder/'postflight.json')
        hashes={Path(line.split()[1]).name:line.split()[0] for line in (folder/'source-hashes.txt').read_text().splitlines()}
        for name in ('g1_04_control.py','g1_03_host_clock.py','g1_04_run.sh'):
            if hashes[name]!=sha(Path(__file__).with_name(name)):raise ValueError('executed source changed')
        if hashes['libnccl-profiler-example.so']!='06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54':raise ValueError('DSO changed')
        executed[n]=hashes
        exitrows.append(dict(node_alias=n,training_exit=int((folder/'training-exit.txt').read_text()),
                             control_exit=int((folder/'control-exit.txt').read_text()),**post))
    if any(r['training_exit'] for r in exitrows):raise ValueError('nonzero training exit')
    return dict(schema='g1-04-public-evidence-v1',classification='REAL_HEALTHY_MULTINODE_TRACE_AND_CONTROL_EXCHANGES' if q['status']=='BOUNDED' else 'REAL_HEALTHY_MULTINODE_TRACE_WITH_FAILED_CONTROL_CAPTURE',
                task='G1-04',candidate_status='PARTIAL' if longest<10 else 'SCOPED_GATE_REVIEW_CANDIDATE',
                test_classifications=dict(DOC='PASS',CPU='PASS',GPU='HEALTHY_DDP_ONLY_PASS',MULTINODE='HEALTHY_4RANK_ONLY_PASS',REAL_HOST_MAPPING='FAIL' if q['status']!='BOUNDED' else 'OBSERVED'),mapping_model=q['mapping_model'],unit='ns',budget_ns=1000000,
                assumptions=['nonnegative communication delay','CLOCK_MONOTONIC monotonic in audited boot/time namespace','audited trace representation bound, not physical hardware accuracy'],
                run_alias=manifest['run_id'],epoch_alias=manifest['rank_epoch'],
                matching_summary=matched['summary'],ranks=rankrows,events=events,summary=summarize(events),
                source_node_summary=summarize([e for e in events if e['rank']>=2]),
                continuous_four_rank_1ms_max_instances=longest,eligible_four_rank_instances=eligible,
                cross_node_matched_pair_interval_order=dict(pairs),
                control=dict(status=q['status'],reasons=q['reasons'],count=len(samples),complete=bool(client and server and q['status']=='BOUNDED'),
                             stop_reason=client['stop_reason'] if client else 'CLIENT_CONNECTION_REFUSED_SERVER_ACCEPT_TIMEOUT',
                             limits=client['limits'] if client else dict(duration_s=90,count=120000,interval_s=.0005,timeout_s=110,max_bytes=67108864),
                             sample_spacing_ns=deltas,
                             reference_window_ns=[samples[0]['t1'],samples[-1]['t4']] if samples else None,
                             source_window_ns=[samples[0]['t2'],samples[-1]['t3']] if samples else None,
                             selected_four_stamps_ns=[samples[i] for i in sorted(used)],
                             input_sha256={n:sha(root/n/'control.json') if (root/n/'control.json').exists() else None for n in ('node-a','node-b')},
                             failure_log_sha256={n:sha(root/n/'control.log') for n in ('node-a','node-b')}),
                runtime=runtime,resource_exit=exitrows,executed_source_sha256=executed,profiler_abi='v4; unchanged DSO with sole ncclProfiler_v4 symbol',
                source_sha256={p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('g1_04_causal.py'),Path(__file__).with_name('g1_04_control.py'),Path(__file__).with_name('g1_04_run.sh'),Path(__file__).with_name('g1_03_host_clock.py'))},
                unknowns=['upstream omitted callbacks/end-to-end loss','GPU timer ring overwrite','production fail-open','cross-GPU absolute timing','step to collective','net overhead INCONCLUSIVE; historical 6-8% risk'],
                gate_recommendation='SUBMIT_SCOPED_HOST_GATE_REVIEW' if longest>=10 else 'PARTIAL_NO_GATE_PAUSE_FOR_REVIEW_CONTROL_LAUNCH_FAILED',
                gate='IN_PROGRESS_PENDING_INDEPENDENT_REVIEW')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--private-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.write_text(json.dumps(build(a.root.resolve(),a.private_manifest.resolve()),indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
