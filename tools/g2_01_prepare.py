#!/usr/bin/env python3
"""Private-capture adapter. Never reads the injection plan, truth or step logs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.g1_01_make_manifest import build_manifest
from tools.g1_01_match_trace import analyze_manifest
from tools.g1_03_audit import validate_audit
from tools.g1_04_causal import validate_capture, map_event
from tools.g1_04_preflight import verify_pair


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Predeclared before capture: dense-DDP gradient AllReduce only. Never select
# operation instances using mapping success, step/episode boundaries or truth.
ANALYSIS_FUNCTION = 'AllReduce'
PINNED_LIBRARIES = {
    'libnccl.so': '618968ee277041751512e619190132a9bdf351c3ce7129c73484f6ef441ad692',
    'libnccl-profiler-example.so': '06740a4ea051720ca974a22a6f448bcacb5648e7a9c4a928e81e043ad88dcf54',
    'libcudart.so': '96c42e418cec19054186b9429c321603cc190bf26a18104e19408117a2a817b0',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def analysis_scope(matches):
    selected = [x for x in matches['instances'] if x['function'] == ANALYSIS_FUNCTION]
    excluded = Counter(x['function'] for x in matches['instances'] if x['function'] != ANALYSIS_FUNCTION)
    return selected, dict(excluded)


def comparability(inputs):
    """Derive opaque comparison tokens from actual capture records, no truth."""
    configurations = []
    mappings = []
    for rank, raw, audit, record in inputs:
        for key, expected in dict(run_id=raw['run_id'],
                                  rank_epoch=raw['rank_epoch'], node_alias=rank['node_alias'],
                                  rank=rank['global_rank'], local_rank=rank['local_rank'],
                                  world_size=4, mode='multinode', warmup=5, steps=40,
                                  batch=32, width=1024, seed=20261020,
                                  torch='2.14.1+cu130', cuda_build='13.0',
                                  nccl_python_version=[2, 30, 7]).items():
            if record.get(key) != expected:
                raise ValueError('capture comparability mismatch: ' + key)
        script = record.get('script_sha256')
        if (not isinstance(script, str) or len(script) != 64
                or any(c not in '0123456789abcdef' for c in script)):
            raise ValueError('missing actual harness hash')
        libraries = []
        for prefix, expected_hash in PINNED_LIBRARIES.items():
            found = [x for x in record['loaded_libraries'] if Path(x['path']).name.startswith(prefix)]
            if not found or any(x.get('sha256') != expected_hash for x in found):
                raise ValueError('loaded DSO mismatch: ' + prefix)
            libraries.append(dict(library=prefix, sha256=expected_hash))
        config = record.get('nccl_config')
        required = {'NCCL_MIN_NCHANNELS', 'NCCL_MAX_NCHANNELS', 'NCCL_MIN_CTAS',
                    'NCCL_MAX_CTAS', 'NCCL_NVLS_NCHANNELS', 'NCCL_PROFILE_EVENT_MASK'}
        if (not isinstance(config, dict) or set(config) != required
                or any(not isinstance(x, str) for x in config.values())
                or config['NCCL_PROFILE_EVENT_MASK'] != '66'):
            raise ValueError('missing/incompatible actual NCCL config')
        configurations.append(dict(script_sha256=script, torch=record['torch'],
                                   cuda_build=record['cuda_build'], nccl=record['nccl_python_version'],
                                   libraries=libraries, nccl_config=config))
        uuid = record.get('gpu_uuid_private')
        if (not isinstance(uuid, str) or not uuid or uuid == 'UNKNOWN'
                or 'H800' not in record.get('gpu_name', '')
                or record.get('device') != rank['local_rank']):
            raise ValueError('GPU rank mapping unavailable')
        mappings.append(dict(rank=rank['global_rank'], node_alias=rank['node_alias'],
                             local_rank=rank['local_rank'], device=record['device'], gpu_uuid=uuid))
    if len(configurations) != 4 or any(c != configurations[0] for c in configurations[1:]):
        raise ValueError('per-rank actual runtime/configuration differs')
    if len({m['rank'] for m in mappings}) != 4 or len({m['gpu_uuid'] for m in mappings}) != 4:
        raise ValueError('nonunique GPU rank mapping')
    return dict(workload='dense-DDP-1024x2-batch32-warmup5-steps40',
                configuration=digest(configurations[0]),
                rank_mapping=digest(sorted(mappings, key=lambda x: x['rank'])))


def prepare(root, manifest_path, role):
    manifest = build_manifest([(n, root/n/'plugin') for n in ('node-a', 'node-b')])
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    manifest_path.chmod(0o600)
    matches = analyze_manifest(manifest_path, redact_identifiers=True)
    controls = [json.loads((root/n/'control.json').read_text()) for n in ('node-a', 'node-b')]
    if verify_pair(*controls)['status'] != 'PASS':
        raise ValueError('control reconciliation failed')
    inputs = []
    for rank in manifest['ranks']:
        folder = root/rank['node_alias']/'plugin'
        raw = json.loads((folder/f"trace_{manifest['world_comm']['comm_hash']}_{rank['comm_rank']}.audit.json").read_text())
        record = json.loads((folder/f"rank-{rank['global_rank']}.json").read_text())
        if record['pid'] != raw['pid'] or record['torch'] != '2.14.1+cu130' or record['nccl_python_version'] != [2, 30, 7]:
            raise ValueError('runtime/PID mismatch')
        expected = {k:rank[k] for k in ('node_alias','pid','comm_rank')}
        expected.update(run_id=manifest['run_id'],rank_epoch=manifest['rank_epoch'],comm_hash=manifest['world_comm']['comm_hash'])
        audit = validate_audit(raw, expected)
        if audit['mapping_status'] != 'OBSERVED' or audit['issues']:
            raise ValueError('invalid audit')
        inputs.append((rank, raw, audit, record))
    comparable = comparability(inputs)
    selected, excluded = analysis_scope(matches)
    q = validate_capture(*controls, [x[1] for x in inputs])
    # complete refers only to all exported/matched rows, never end-to-end callback completeness.
    clean = q['status'] == 'BOUNDED' and bool(selected) and all(x['status']=='MATCHED' for x in selected)
    instance_rows = {}
    audit_summaries = []
    for rank, raw, audit, record in inputs:
        for name in ('Group','Coll'):
            cls=raw['classes'][name]
            if not cls['callback_attempted']==cls['pool_accepted']==cls['exported']: clean=False
            for k in ('known_pool_drop','parent_rejected','guard_rejected'):
                if cls.get(k) != 0: clean = False
        audit_summaries.append(dict(rank=rank['global_rank'],audit=audit))
        for event in json.loads(Path(rank['trace_file']).read_text()):
            if (event.get('cat') != 'COLL' or event.get('ph') != 'b'
                    or event.get('name') != ANALYSIS_FUNCTION): continue
            if event['pid'] != raw['pid'] or event['args']['Rank'] != rank['comm_rank']:
                raise ValueError('trace identity mismatch')
            stamp = raw['origin_monotonic_ns'] + round(event['ts']*1000)
            mapped = map_event(q, raw, stamp, raw['origin_mapping_error_ns'])
            key = (event['name'], event['args']['SeqNum'])
            instance_rows.setdefault(key, []).append(dict(rank=rank['global_rank'],status=mapped['status'],start=mapped['reference_interval_ns'],source_ns=stamp))
    instances = []
    for match in selected:
        # Matcher output metadata is the canonical comparable operation signature.
        key = (match['function'],match['seq_num'])
        row = {k:match.get(k) for k in ('function','seq_num','count','datatype','algorithm','protocol','n_channels','status')}
        row['comm_hash'] = 'WORLD'  # validated membership, raw hash not exposed
        row['ranks'] = sorted(instance_rows.get(key,[]), key=lambda x:x['rank'])
        instances.append(row)
    return dict(schema='g2-01-host-intervals-v1', role=role, run_id=manifest['run_id'],rank_epoch=manifest['rank_epoch'],
                reference_clock='reference-'+sha(manifest_path)[:16],unit='ns',expected_ranks=[0,1,2,3],
                comparability=comparable,
                quality=dict(status='BOUNDED' if q['status']=='BOUNDED' else 'UNSAFE',complete=clean),instances=instances,
                evidence=dict(matching_summary=matches['summary'],audits=audit_summaries,control_status=q['status'],
                              analysis_scope=dict(function=ANALYSIS_FUNCTION,selection='OPERATION_TYPE_ONLY_INCLUDES_WARMUP',
                                                  selected_instances=len(selected),excluded_instance_counts=excluded),
                              source_sha256={p.name:sha(p) for p in (Path(__file__),Path(__file__).with_name('g1_04_causal.py'))},
                              upstream_omitted_callbacks='UNKNOWN',clock_semantics='HOST_CALLBACK_ONLY'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--quality-output',type=Path,required=True)
    p.add_argument('--role',choices=['HEALTHY_BASELINE','OBSERVED'],required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();doc=prepare(a.root,a.manifest,a.role)
    evidence=doc.pop('evidence')
    with a.quality_output.open('x') as f:json.dump(evidence,f,indent=2,allow_nan=False);f.write('\n')
    with a.output.open('x') as f:json.dump(doc,f,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':main()
