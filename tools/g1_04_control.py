#!/usr/bin/env python3
"""Bounded continuous private Host sidecar; independent of training and GPUs."""
import argparse
import socket
import time
from g1_03_host_clock import metadata, now, _send, _remaining, _write_private
import json
import math

MAX_SAMPLES = 120000
MAX_BYTES = 64 * 1024 * 1024

def receive(sock, deadline):
    data = bytearray()
    while len(data) < 16384:
        _remaining(sock, deadline)
        block = sock.recv(16384-len(data))
        stamp = now()
        if not block:
            raise ValueError('truncated message')
        data.extend(block)
        if b'\n' in block:
            if data[-1:] != b'\n' or data.count(b'\n') != 1:
                raise ValueError('unexpected framing/read ahead')
            return json.loads(data), stamp
    raise ValueError('packet limit')

def run(role, address, port, identity, duration, count, interval, timeout):
    if role not in {'client','server'} or type(count) is not int or any(type(x) not in (int,float) or not math.isfinite(x) for x in (duration,interval,timeout)):
        raise ValueError('invalid control parameters')
    if not 1 <= count <= MAX_SAMPLES or not 1 <= duration <= 100 or not .0005 <= interval <= 1 or not duration+5 <= timeout <= 120:
        raise ValueError('bounded collection limits invalid')
    socket.inet_pton(socket.AF_INET,address)
    doc = dict(schema='g1-04-host-control-v1', classification='REAL_HOST_CONTROL',
               transport='INDEPENDENT_TCP_CONTROL', phase='continuous', unit='ns',
               privacy='PRIVATE', exchanges=[], complete=False,
               limits=dict(duration_s=duration,count=count,interval_s=interval,timeout_s=timeout,max_bytes=MAX_BYTES))
    deadline=time.monotonic()+timeout
    listener=None
    try:
        if role=='server':
            listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((address,port));listener.listen(1);_remaining(listener,deadline)
            connection,_=listener.accept();doc['source']=identity
        else:
            connection=socket.create_connection((address,port),timeout=timeout);doc['reference']=identity
        with connection:
            connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            stop=time.monotonic()+duration
            size=0
            for index in range(count):
                if role=='client':
                    request=dict(run=identity['run'],epoch=identity['epoch'],index=index,stop=time.monotonic()>=stop)
                    request['t1']=now();_send(connection,request,deadline)
                    response,t4=receive(connection,deadline)
                    if any(response.get(k)!=v for k,v in request.items()): raise ValueError('response mismatch')
                    if index and doc['source']!=response['source']: raise ValueError('source identity changed')
                    doc['source']=response['source']
                    row={k:response[k] for k in ('index','t1','t2','t3')};row['t4']=t4
                else:
                    request,t2=receive(connection,deadline)
                    if request.get('index')!=index or request.get('run')!=identity['run'] or request.get('epoch')!=identity['epoch']: raise ValueError('request mismatch')
                    response={**request,'t2':t2,'source':identity};response['t3']=now()
                    _send(connection,response,deadline)
                    row={k:response[k] for k in ('index','t1','t2','t3')}
                size+=len(json.dumps(row))+2
                if size>MAX_BYTES: raise ValueError('file budget exceeded')
                doc['exchanges'].append(row)
                if request['stop']:
                    doc['complete']=True;doc['stop_reason']='DURATION_LIMIT';break
                if role=='client': time.sleep(interval)
            else: doc['complete']=True;doc['stop_reason']='COUNT_LIMIT'
    finally:
        if listener: listener.close()
    doc['count']=len(doc['exchanges'])
    return doc

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('role',choices=('server','client'));p.add_argument('--address',required=True);p.add_argument('--port',type=int,required=True)
    for k in ('run','epoch','node','output'):p.add_argument('--'+k,required=True)
    p.add_argument('--duration',type=float,default=90);p.add_argument('--count',type=int,default=120000)
    p.add_argument('--interval',type=float,default=.0005);p.add_argument('--timeout',type=float,default=110)
    a=p.parse_args();_write_private(a.output,run(a.role,a.address,a.port,metadata(a.run,a.epoch,a.node),a.duration,a.count,a.interval,a.timeout))
if __name__=='__main__':main()
