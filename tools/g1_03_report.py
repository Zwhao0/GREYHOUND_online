#!/usr/bin/env python3
"""Build a redacted G1-03 report from PRIVATE two-node archives (CPU offline)."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.g1_01_make_manifest import build_manifest
from tools.g1_01_match_trace import analyze_manifest as match
from tools.g1_02_capture_quality import analyze_manifest as capture
from tools.g1_03_audit import validate_audit
from tools.g1_03_host_clock import verify_real_capture, map_source_time


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_report(root: Path, manifest_path: Path, executed_clock_source: Path | None = None):
    manifest = build_manifest([(n, root/n/'plugin') for n in ('node-a', 'node-b')])
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    manifest_path.chmod(0o600)
    matched, captured = match(manifest_path, redact_identifiers=True), capture(manifest_path)
    audits, rows, performance, runtime, sources, exits = [], [], [], [], {}, []
    for rank in manifest['ranks']:
        node, index = rank['node_alias'], rank['global_rank']
        folder = root/node/'plugin'
        raw = read(folder/f"trace_{manifest['world_comm']['comm_hash']}_{rank['comm_rank']}.audit.json")
        record = read(folder/f'rank-{index}.json')
        expected = {k:rank[k] for k in ('node_alias','pid','comm_rank')}
        expected.update(run_id=manifest['run_id'],rank_epoch=manifest['rank_epoch'],comm_hash=manifest['world_comm']['comm_hash'])
        audit = validate_audit(raw,expected)
        if audit['mapping_status'] != 'OBSERVED' or audit['issues']:
            raise ValueError('audit identity/export inconsistency')
        trace = next(r for r in captured['ranks'] if r['identity']['global_rank']==index)
        error=raw.get('origin_mapping_error_ns')
        if type(error) is not int or error <= 0:
            raise ValueError('origin numerical mapping error missing')
        first,last=[raw['origin_monotonic_ns']+round(trace['exported_window'][k]*1000) for k in ('minimum_ts','maximum_ts')]
        if not raw['origin_monotonic_ns'] <= first-error <= last+error <= raw['active_until_monotonic_ns']:
            raise ValueError('trace timestamps outside audited local Host window')
        for cls, observed in trace['event_classes'].items():
            if cls in audit['classes']:
                if audit['classes'][cls]['counters']['exported'] != observed['observed_begin_count']:
                    raise ValueError('export counter/trace mismatch')
        audits.append(raw)
        rows.append({'global_rank':index,'input_trace_sha256':trace['trace_input']['sha256'],
                     'input_audit_sha256':sha(Path(str(rank['trace_file']).removesuffix('.json')+'.audit.json')),
                     'operations':trace['operations'],'event_classes':trace['event_classes'],
                     'host_origin_mapping':{'status':'OBSERVED','unit':'ns','api':'CLOCK_MONOTONIC',
                                            'trace_window_absolute_ns':[first,last],'representation_error_ns':error,
                                            'meaning':'local numerical mapping only; no hardware accuracy or cross-node drift claim'},
                     'collector_audit':audit,'end_to_end_loss':'UNKNOWN','gpu_timer_ring_overwrite':'UNKNOWN'})
        baseline = read(root/node/'baseline'/f'rank-{index}.json')
        perf={'global_rank':index}
        for mode,data in [('baseline',baseline),('plugin',record)]:
            perf[mode]={k:data[k] for k in ('gpu_step_ms','gpu_p50_ms','gpu_p95_ms','max_rss_kib','max_torch_allocated_bytes','max_torch_reserved_bytes')}
            if data['torch']!='2.14.1+cu130' or data['nccl_python_version']!=[2,30,7]:
                raise ValueError('runtime version changed')
            dsos=[{'basename':Path(lib['path']).name,**{k:v for k,v in lib.items() if k in ('sha256','version','version_query_status')}} for lib in data['loaded_libraries']]
            runtime.append({'global_rank':index,'mode':mode,'torch':data['torch'],'nccl':data['nccl_python_version'],'dsos':dsos})
        perf['p50_change_percent']=(record['gpu_p50_ms']/baseline['gpu_p50_ms']-1)*100
        perf['p95_change_percent']=(record['gpu_p95_ms']/baseline['gpu_p95_ms']-1)*100
        performance.append(perf)
    for node in ('node-a','node-b'):
        summary=read(root/node/'private-summary.json')
        sources[node]={'summary_sha256':sha(root/node/'private-summary.json'),
                       'executed_sources_sha256':{Path(k).name:v for k,v in summary['hashes'].items() if 'libnccl-profiler' not in k},
                       'old_profiler_unchanged_sha256':next(v for k,v in summary['hashes'].items() if 'g1_01_20261020/' in k)}
        exits.append({'node_alias':node,'task_processes_remaining':summary['task_processes_remaining'],
                      'gpu_application_count_after':summary['gpu_application_count'],
                      'launcher_exits':{m:d['launcher_exit'] for m,d in summary['modes'].items()}})
    pre,post=[read(root/'node-a'/f'{phase}-client.json') for phase in ('pre','post')]
    # Cross-check independent server evidence rather than trusting a client file alone.
    for phase,client in [('pre',pre),('post',post)]:
        server=read(root/'node-b'/f'{phase}-server.json')
        if server['source'] != client['source'] or server['exchanges'] != [{k:s[k] for k in ('t1','t2','t3')} for s in client['exchanges']]:
            raise ValueError('control server/client evidence mismatch')
    clocks=verify_real_capture(pre,post,audits)
    # Raw identities stay private; timestamps are deliberately retained as ns evidence.
    clocks.pop('reference',None);clocks.pop('source',None)
    origin_maps=[]
    for raw in audits:
        if raw['node_alias']=='node-b':
            mapped=map_source_time(raw['origin_monotonic_ns'],clocks,raw['origin_mapping_error_ns'])
            mapped.update(global_rank=raw['comm_rank'],source_host_origin_ns=raw['origin_monotonic_ns'])
            low,high=mapped['reference_interval_ns']
            mapped['source_minus_reference_offset_interval_ns']=[raw['origin_monotonic_ns']-high,raw['origin_monotonic_ns']-low]
            origin_maps.append(mapped)
    source_verification={'status':'UNKNOWN','reason':'executed source file not supplied'}
    if executed_clock_source is not None:
        current=Path(__file__).with_name('g1_03_host_clock.py')
        def functions(path):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
        a,b=functions(executed_clock_source),functions(current)
        names=('now','metadata','_limits','_remaining','_send','_receive','_document','serve','collect','_write_private','main')
        if any(a.get(k)!=b.get(k) for k in names) or any(sha(executed_clock_source)!=sources[node]['executed_sources_sha256']['g1_03_host_clock.py'] for node in sources):
            raise ValueError('executed control collector differs from committed runtime functions')
        source_verification={'status':'OBSERVED','executed_sha256':sha(executed_clock_source),
                             'current_sha256':sha(current),'runtime_functions_ast_identical':True,
                             'difference_scope':'offline verification helpers only; no runtime rerun claimed'}
    return {'schema_name':'CaptureQuality','schema_version':2,'task':'G1-03','candidate_status':'PARTIAL',
            'test_classifications':{'DOC':'PASS','CPU':'PASS','MULTINODE':'PASS_SCOPED_HEALTHY_DDP','GPU':'PASS_SCOPED_HEALTHY_DDP'},
            'source_classification':'REAL_HEALTHY_MULTINODE_TRACE_AND_CONTROL_EXCHANGES',
            'world':captured['world'],'matching_summary':matched['summary'],'ranks':rows,
            'host_clock':clocks,'source_origin_maps':origin_maps,
            'raw_four_stamps_ns':{'pre':pre['exchanges'],'post':post['exchanges']},
            'clock_input_sha256':{f'{phase}-{role}':sha(root/node/f'{phase}-{role}.json') for phase in ('pre','post') for role,node in [('client','node-a'),('server','node-b')]},
            'gpu_clock':{'status':'UNSAFE','usable_for_cross_rank':False,'calibration':'UNKNOWN','step_to_coll':'UNKNOWN'},
            'performance':{'classification':'ONE_SEQUENTIAL_SHARED_RESOURCE_PAIR_INCONCLUSIVE_OVERHEAD','ranks':performance,
                           'historical_g1_01_p50_increase_percent':[6.10,7.53],'overhead_sla':'NOT_ESTABLISHED'},
            'runtime':runtime,'private_evidence_sources':sources,'control_source_verification':source_verification,'resource_exit':exits,
            'unresolved':['continuous training-window drift/offset bound insufficient for useful Host comparisons',
                          'upstream GPU timer ring loss, upstream missing callbacks and full-history completeness UNKNOWN',
                          'shared short-run overhead is inconclusive; historical6-8percent risk remains'],
            'gate':'IN_PROGRESS_NOT_SUBMITTED_AS_PASS'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_root',type=Path);p.add_argument('--private-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--executed-clock-source',type=Path)
    a=p.parse_args()
    result=build_report(a.private_root.resolve(),a.private_manifest.resolve(),a.executed_clock_source)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')


if __name__=='__main__':
    main()
