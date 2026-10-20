#!/usr/bin/env python3
"""G0-03: one-node, two-H800 synthetic dense DDP; no diagnostic collectives."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import time

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP


def percentile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = int(pos)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (pos - lo)


def libraries():
    paths = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                    if '/' in line and ('libnccl.so' in line or 'libnccl-profiler' in line)})
    result = []
    for path in paths:
        digest = hashlib.sha256()
        with open(path, 'rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        entry = {'path': path, 'sha256': digest.hexdigest()}
        if 'libnccl.so' in path:
            version = ctypes.c_int()
            call = ctypes.CDLL(path).ncclGetVersion
            call.argtypes = [ctypes.POINTER(ctypes.c_int)]
            call.restype = ctypes.c_int
            entry.update(version_query_status=call(ctypes.byref(version)), version=version.value)
        result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--warmup', type=int, default=5)
    args = parser.parse_args()
    rank, local = int(os.environ['RANK']), int(os.environ['LOCAL_RANK'])
    if int(os.environ['WORLD_SIZE']) != 2 or int(os.environ['LOCAL_WORLD_SIZE']) != 2:
        raise RuntimeError('Only single-node two-rank execution is allowed')
    if torch.cuda.device_count() != 2 or 'H800' not in torch.cuda.get_device_name(local):
        raise RuntimeError('Expose exactly two authorized H800 devices')
    if not 1 <= args.steps <= 40 or not 0 <= args.warmup <= 5:
        raise RuntimeError('Short PoC only')
    torch.set_num_threads(1)
    torch.manual_seed(20261020)
    torch.cuda.set_device(local)
    dist.init_process_group('nccl')
    model = DDP(torch.nn.Sequential(torch.nn.Linear(1024, 1024), torch.nn.ReLU(),
                                   torch.nn.Linear(1024, 1024)).cuda(), device_ids=[local])
    optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
    inputs = torch.randn(32, 1024, device='cuda')
    def step():
        optimizer.zero_grad(set_to_none=True)
        model(inputs).square().mean().backward()
        optimizer.step()
    for _ in range(args.warmup):
        step()
    torch.cuda.synchronize()  # Warmup boundary, never within a training step.
    loaded = libraries()  # Evidence from this DDP PID after communicator initialization.
    events = [(torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True))
              for _ in range(args.steps)]
    host_ms = []
    start = time.perf_counter()
    for begin, end in events:
        host_start = time.perf_counter()
        begin.record()
        step()
        end.record()
        host_ms.append((time.perf_counter() - host_start) * 1000)
    torch.cuda.synchronize()  # One measurement boundary before reading all CUDA events.
    wall_ms = (time.perf_counter() - start) * 1000
    gpu_ms = [begin.elapsed_time(end) for begin, end in events]
    record = {
        'rank': rank, 'local_rank': local, 'world_size': dist.get_world_size(), 'pid': os.getpid(),
        'device': local, 'gpu_name': torch.cuda.get_device_name(local),
        'torch': torch.__version__, 'cuda_build': torch.version.cuda, 'loaded_libraries': loaded,
        'process_group': {'backend': dist.get_backend(), 'members': [0, 1],
                          'name': str(getattr(dist.group.WORLD, 'group_name', 'UNKNOWN'))},
        'warmup': args.warmup, 'steps': args.steps, 'batch': 32, 'width': 1024, 'seed': 20261020,
        'gpu_step_ms': gpu_ms, 'host_dispatch_step_ms': host_ms,
        'gpu_p50_ms': statistics.median(gpu_ms), 'gpu_p95_ms': percentile(gpu_ms, .95),
        'host_p50_ms': statistics.median(host_ms), 'host_p95_ms': percentile(host_ms, .95),
        'wall_ms_per_step': wall_ms / args.steps,
        'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'max_torch_allocated_bytes': torch.cuda.max_memory_allocated(local),
        'step_to_collective': 'UNKNOWN; no collector step marker or cross-clock matching',
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f'rank-{rank}.json').write_text(json.dumps(record, indent=2) + '\n')
    dist.destroy_process_group()


if __name__ == '__main__':
    main()
