#!/usr/bin/env python3
"""G1-01: bounded synthetic dense DDP smoke or two-node capture; no diagnostic collectives."""
import argparse
import ctypes
from datetime import timedelta
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

if __package__:
    from .g2_01_inject import (
        ensure_separate_output, episode_for, load_plan, sleep_for_episode,
        validate_capture_bounds, write_rank_truth,
    )
else:
    from g2_01_inject import (
        ensure_separate_output, episode_for, load_plan, sleep_for_episode,
        validate_capture_bounds, write_rank_truth,
    )


def percentile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = int(pos)
    return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (pos - lo)


def libraries():
    paths = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                    if '/' in line and ('libnccl.so' in line or 'libnccl-profiler' in line or 'libcudart.so' in line)})
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
        if 'libcudart.so' in path:
            version = ctypes.c_int()
            call = ctypes.CDLL(path).cudaRuntimeGetVersion
            call.argtypes = [ctypes.POINTER(ctypes.c_int)]
            call.restype = ctypes.c_int
            entry.update(version_query_status=call(ctypes.byref(version)), version=version.value)
        result.append(entry)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--rank-epoch', required=True)
    parser.add_argument('--node-alias', choices=['node-a', 'node-b'], required=True)
    parser.add_argument('--mode', choices=['smoke', 'multinode'], required=True)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--warmup', type=int, default=5)
    parser.add_argument('--g2-plan', type=Path,
                        help='private G2-01 injection plan; omitted for a healthy run')
    parser.add_argument('--g2-truth-output', type=Path,
                        help='separate private directory for G2-01 truth timestamps')
    args = parser.parse_args()
    rank, local = int(os.environ['RANK']), int(os.environ['LOCAL_RANK'])
    expected = 2 if args.mode == 'smoke' else 4
    if int(os.environ['WORLD_SIZE']) != expected or int(os.environ['LOCAL_WORLD_SIZE']) != 2:
        raise RuntimeError('Only two local ranks and bounded 2/4-rank execution are allowed')
    expected_node = 0 if args.node_alias == 'node-a' else 1
    if rank // 2 != expected_node:
        raise RuntimeError('Launcher global/local rank to node mapping mismatch')
    torch.cuda.set_device(local)
    if torch.cuda.device_count() != 2 or 'H800' not in torch.cuda.get_device_name(local):
        raise RuntimeError('Expose exactly two authorized H800 devices')
    if not 1 <= args.steps <= 40 or not 0 <= args.warmup <= 5:
        raise RuntimeError('Short PoC only')
    if args.g2_plan is not None and args.g2_truth_output is None:
        raise RuntimeError('--g2-plan requires --g2-truth-output')
    if args.g2_truth_output is not None:
        ensure_separate_output(args.g2_truth_output, args.output)
        validate_capture_bounds(steps=args.steps, warmup=args.warmup,
                                world_size=int(os.environ['WORLD_SIZE']))
    g2_plan = None
    if args.g2_plan is not None:
        g2_plan = load_plan(args.g2_plan, steps=args.steps, warmup=args.warmup,
                            world_size=int(os.environ['WORLD_SIZE']))
    torch.set_num_threads(1)
    torch.manual_seed(20261020)
    torch.cuda.set_per_process_memory_fraction(0.01, local)  # ~800 MiB allocator cap; context/NCCL excluded.
    dist.init_process_group('nccl', timeout=timedelta(seconds=60))
    model = DDP(torch.nn.Sequential(torch.nn.Linear(1024, 1024), torch.nn.ReLU(),
                                   torch.nn.Linear(1024, 1024)).cuda(), device_ids=[local])
    optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
    inputs = torch.randn(32, 1024, device='cuda')
    def step(measured_step=None):
        optimizer.zero_grad(set_to_none=True)
        loss = model(inputs).square().mean()
        episode = episode_for(g2_plan, step=measured_step, rank=rank) if measured_step is not None else None
        injection_truth = sleep_for_episode(episode)
        loss.backward()
        optimizer.step()
        return injection_truth
    loaded = libraries()  # Same DDP PID, after comm init; hash before warmup.
    for _ in range(args.warmup):
        step()
    torch.cuda.synchronize()  # Warmup boundary, never within a training step.
    events = [(torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True))
              for _ in range(args.steps)]
    host_ms = []
    step_boundaries = []
    start = time.perf_counter()
    for measured_step, (begin, end) in enumerate(events):
        host_start = time.perf_counter()
        step_start_ns = time.monotonic_ns()
        begin.record()
        injection_truth = step(measured_step)
        end.record()
        step_end_ns = time.monotonic_ns()
        host_ms.append((time.perf_counter() - host_start) * 1000)
        step_boundaries.append({
            'step': measured_step,
            'start_monotonic_ns': step_start_ns,
            'end_monotonic_ns': step_end_ns,
            'injection': injection_truth,
        })
    torch.cuda.synchronize()  # One measurement boundary before reading all CUDA events.
    wall_ms = (time.perf_counter() - start) * 1000
    gpu_ms = [begin.elapsed_time(end) for begin, end in events]
    record = {
        'run_id': args.run_id, 'rank_epoch': args.rank_epoch, 'node_alias': args.node_alias,
        'mode': args.mode, 'rank': rank, 'local_rank': local, 'world_size': dist.get_world_size(), 'pid': os.getpid(),
        'device': local, 'cuda_visible_devices': os.environ['CUDA_VISIBLE_DEVICES'],
        'gpu_uuid_private': str(getattr(torch.cuda.get_device_properties(local), 'uuid', 'UNKNOWN')),
        'gpu_name': torch.cuda.get_device_name(local),
        'torch': torch.__version__, 'cuda_build': torch.version.cuda, 'loaded_libraries': loaded,
        'process_group': {'backend': dist.get_backend(), 'members': dist.get_process_group_ranks(dist.group.WORLD),
                          'name': str(getattr(dist.group.WORLD, 'group_name', 'UNKNOWN'))},
        'allocator_fraction_cap': 0.01,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'nccl_config': {name: os.environ.get(name, 'UNSET') for name in (
            'NCCL_MIN_NCHANNELS', 'NCCL_MAX_NCHANNELS', 'NCCL_MIN_CTAS',
            'NCCL_MAX_CTAS', 'NCCL_NVLS_NCHANNELS', 'NCCL_PROFILE_EVENT_MASK')},
        'warmup': args.warmup, 'steps': args.steps, 'batch': 32, 'width': 1024, 'seed': 20261020,
        'gpu_step_ms': gpu_ms, 'host_dispatch_step_ms': host_ms,
        'gpu_p50_ms': statistics.median(gpu_ms), 'gpu_p95_ms': percentile(gpu_ms, .95),
        'host_p50_ms': statistics.median(host_ms), 'host_p95_ms': percentile(host_ms, .95),
        'wall_ms_per_step': wall_ms / args.steps,
        'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'max_torch_allocated_bytes': torch.cuda.max_memory_allocated(local),
        'max_torch_reserved_bytes': torch.cuda.max_memory_reserved(local),
        'nccl_python_version': list(torch.cuda.nccl.version()),
        'sampling_boundary': 'whole process; CUDA synchronization only after warmup and measurement',
        'step_to_collective': 'UNKNOWN; no collector step marker or cross-clock matching',
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f'rank-{rank}.json').write_text(json.dumps(record, indent=2) + '\n')
    if args.g2_truth_output is not None:
        write_rank_truth(args.g2_truth_output, rank=rank, steps=args.steps, warmup=args.warmup,
                         plan=g2_plan, step_boundaries=step_boundaries)
    dist.destroy_process_group()


if __name__ == '__main__':
    main()
