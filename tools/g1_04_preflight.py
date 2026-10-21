#!/usr/bin/env python3
"""Independent CPU/network preflight. PASS never establishes training precision."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import socket
from pathlib import Path
import sys
try:
    from .g1_03_host_clock import _identity,_integer,_write_private
except ImportError:
    from g1_03_host_clock import _identity,_integer,_write_private


def validate_config(ddp_master_addr,control_source_addr,reference_node='node-a',source_node='node-b'):
    for value in (ddp_master_addr,control_source_addr):
        try:socket.inet_pton(socket.AF_INET,value)
        except (OSError,TypeError):raise ValueError('literal IPv4 required')
        if value in ('0.0.0.0','255.255.255.255') or value.startswith('127.'):
            raise ValueError('routable private role-specific endpoints required')
    if ddp_master_addr==control_source_addr:raise ValueError('DDP reference and control source addresses must differ')
    if reference_node!='node-a' or source_node!='node-b':raise ValueError('expected node-a reference and node-b source')


def verify_pair(client,server,reference_node='node-a',source_node='node-b'):
    result=dict(status='FAIL',classification='CPU_NETWORK_ONLY',training_calibration=False,reasons=[])
    try:
        for doc in (client,server):
            for key,value in dict(schema='g1-04-host-control-v1',classification='REAL_HOST_CONTROL',transport='INDEPENDENT_TCP_CONTROL',phase='continuous',unit='ns',complete=True).items():
                if doc.get(key)!=value or key=='complete' and doc[key] is not True:raise ValueError('invalid control schema/completion/unit')
            count=_integer(doc.get('count'),'count')
            if not isinstance(doc.get('exchanges'),list) or not 2<=count==len(doc['exchanges'])<=120000:raise ValueError('control count/missing samples')
        ref,src=(_identity(client.get(k)) for k in ('reference','source'))
        if ref[:2]!=src[:2] or ref[2]!=reference_node or src[2]!=source_node or ref[5]==src[5]:raise ValueError('run/epoch/host role identity mismatch')
        if server.get('source')!=client['source'] or server.get('reference')!=client['reference']:raise ValueError('independent peer/PID identity mismatch')
        if client['count']!=server['count']:raise ValueError('independent count mismatch')
        last=(-1,-1)
        for i,(a,b) in enumerate(zip(client['exchanges'],server['exchanges'])):
            if type(a.get('index')) is not int or a['index']!=i or b!={k:a[k] for k in ('index','t1','t2','t3')}:raise ValueError('independent four-stamp/sequence mismatch')
            t1,t2,t3,t4=(_integer(a[k],k) for k in ('t1','t2','t3','t4'))
            if t1<last[0] or t2<last[1] or t4<t1 or t3<t2:raise ValueError('nonmonotonic local clock')
            last=(t4,t3)
        result.update(status='PASS',count=client['count'],run=ref[0],epoch=ref[1],peer_binding='OBSERVED_BOTH_ENDS',reference=client['reference'],source=client['source'])
    except (ValueError,TypeError,KeyError,AttributeError) as exc:result['reasons'].append(str(exc))
    return result


def verify_live_process(identity, start_ticks):
    pid=identity['pid']
    os.kill(pid,0)
    proc=Path('/proc')/str(pid)
    if not proc.exists():raise ValueError('Linux live process provenance required')
    ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])
    if type(start_ticks) is not int or ticks!=start_ticks:raise ValueError('collector process incarnation changed')
    if os.readlink(proc/'ns/time')!=identity['time_namespace'] or os.readlink(proc/'ns/pid')!=identity['pid_namespace'] or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=identity['boot_id']:
        raise ValueError('live collector clock domain changed')
    if b'g1_04_control.py' not in (proc/'cmdline').read_bytes():raise ValueError('live PID is not collector')


def verify_ready(marker, proof, run, epoch, node, collector_source):
    if proof.get('status')!='PASS' or proof.get('classification')!='CPU_NETWORK_ONLY' or proof.get('training_calibration') is not False:
        raise ValueError('successful independent CPU preflight proof required')
    if marker.get('status')!='CONTROL_READY' or marker.get('unit')!='ns':raise ValueError('validated readiness marker required')
    own,peer=marker['self'],marker['peer']
    a,b=_identity(own),_identity(peer)
    other='node-b' if node=='node-a' else 'node-a'
    if a[:3]!=(run,epoch,node) or b[:3]!=(run,epoch,other) or a[5]==b[5]:raise ValueError('ready run/epoch/roles mismatch')
    for identity in (own,peer):
        expected=proof['reference' if identity['node']=='node-a' else 'source']
        if _identity(identity)[2:]!=_identity(expected)[2:]:raise ValueError('preflight clock domain changed')
    digest=hashlib.sha256(Path(collector_source).read_bytes()).hexdigest()
    if proof.get('collector_sha256')!=digest:raise ValueError('collector changed since preflight')
    helper=Path(collector_source).with_name('g1_03_host_clock.py')
    if proof.get('host_helper_sha256')!=hashlib.sha256(helper.read_bytes()).hexdigest():raise ValueError('timestamp helper changed since preflight')
    if marker['first_exchange'].get('index')!=0:raise ValueError('first complete exchange missing')
    verify_live_process(own,marker.get('process_start_ticks'))
    return dict(status='PASS',classification='CPU_NETWORK_READY_ONLY',run=run,epoch=epoch,node=node)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    c=sub.add_parser('config')
    for key in ('ddp-master-addr','control-source-addr'):c.add_argument('--'+key,required=True)
    v=sub.add_parser('verify')
    for key in ('client','server','client-exit','server-exit','collector-source','output'):v.add_argument('--'+key,type=Path,required=True)
    for key in ('ddp-master-addr','control-source-addr'):v.add_argument('--'+key,required=True)
    r=sub.add_parser('ready')
    for key in ('marker','proof','collector-source'):r.add_argument('--'+key,type=Path,required=True)
    for key in ('run','epoch','node'):r.add_argument('--'+key,required=True)
    a=p.parse_args()
    if a.mode=='ready':
        result=verify_ready(json.loads(a.marker.read_text()),json.loads(a.proof.read_text()),a.run,a.epoch,a.node,a.collector_source)
    elif a.mode=='config':
        validate_config(a.ddp_master_addr,a.control_source_addr);result=dict(status='PASS',classification='CONFIG_ONLY')
    else:
        validate_config(a.ddp_master_addr,a.control_source_addr)
        client,server=(json.loads(path.read_text()) for path in (a.client,a.server))
        result=verify_pair(client,server)
        if a.client_exit.read_text().strip()!='0' or a.server_exit.read_text().strip()!='0':result.update(status='FAIL',reasons=result['reasons']+['control exit not zero'])
        digest=hashlib.sha256(a.collector_source.read_bytes()).hexdigest()
        if client.get('collector_sha256')!=digest or server.get('collector_sha256')!=digest:result.update(status='FAIL',reasons=result['reasons']+['executed collector source mismatch'])
        helper_digest=hashlib.sha256(a.collector_source.with_name('g1_03_host_clock.py').read_bytes()).hexdigest()
        if client.get('host_helper_sha256')!=helper_digest or server.get('host_helper_sha256')!=helper_digest:result.update(status='FAIL',reasons=result['reasons']+['executed timestamp helper mismatch'])
        result['host_helper_sha256']=helper_digest
        result['collector_sha256']=digest
        result['input_sha256']={k:hashlib.sha256(getattr(a,k).read_bytes()).hexdigest() for k in ('client','server','client_exit','server_exit')}
        _write_private(a.output,result)
    print(result['status'])
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
