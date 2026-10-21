"""Bounded orchestration barriers, independent of SSH credentials and GPUs.

Use one controller process for both nodes: never insert model/tool turns between
starting the source, observing its listener, and starting the reference client.
The caller owns private transport adapters and must verify complete paired
preflight evidence before providing any training-start callback.
"""
import time


def wait_for(predicate, *, timeout_s=10, poll_s=.05):
    if not 0<timeout_s<=30 or not 0<poll_s<=1:raise ValueError('bounded barrier parameters required')
    deadline=time.monotonic()+timeout_s
    while True:
        if predicate():return
        if time.monotonic()>=deadline:raise TimeoutError('orchestration readiness deadline expired')
        time.sleep(min(poll_s,max(0,deadline-time.monotonic())))


def start_control_pair(start_source,source_listening,start_reference,*,timeout_s=10):
    source=start_source()
    wait_for(source_listening,timeout_s=timeout_s)
    reference=start_reference()
    return source,reference


def start_training_pair(verify_complete_preflight,both_sidecars_ready,start_reference,start_source):
    # Both callbacks must validate evidence, not merely file existence. The
    # callback return values are explicit; a falsey/missing status fails closed.
    if verify_complete_preflight() is not True:raise ValueError('complete independent preflight PASS required')
    if both_sidecars_ready() is not True:raise ValueError('both live validated sidecars required')
    reference=start_reference()
    source=start_source()
    return reference,source
