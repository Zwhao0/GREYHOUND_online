#!/usr/bin/env bash
# Issue #3: existing official nccl-tests; one local node, exactly two visible GPUs.
# Requires separately authorized shared/test resources. No sudo or installation.
# Usage: CUDA_VISIBLE_DEVICES=0,1 bash tools/g0_02_nccl_poc.sh MODE PRIVATE_DIR [PLUGIN_SO]
# MODE=baseline|plugin|rollback. Build the official plugin separately, unchanged.
set -euo pipefail
mode=${1:?baseline, plugin, or rollback}
private_dir=${2:?private output directory}
export G002_PLUGIN=${3:-}
case "$mode" in
  baseline) export G002_ITERS=40 G002_WARMUP=5 ;;
  plugin) test -f "$G002_PLUGIN"; export G002_ITERS=40 G002_WARMUP=5 ;;
  rollback) export G002_ITERS=2 G002_WARMUP=0 ;;
  *) exit 2 ;;
esac
case "${CUDA_VISIBLE_DEVICES:?select exactly two authorized GPUs}" in
  *,*,*|*,|,*) echo 'Select exactly two GPUs' >&2; exit 2 ;;
  *,*) ;;
  *) echo 'Select exactly two GPUs' >&2; exit 2 ;;
esac
mkdir -p "$private_dir/$mode"
export G002_OUTPUT=$(cd "$private_dir/$mode" && pwd)
export G002_MODE=$mode
# These defaults describe the tested installation; override only to existing tools.
export G002_BINARY=${G002_BINARY:-/opt/nccl-tests/bin/all_reduce_perf}
mpi=${G002_MPI:-/usr/mpi/gcc/openmpi-4.1.9a1/bin/mpirun}
set +e
timeout --signal=TERM --kill-after=5s 120s "$mpi" -np 2 --host localhost:2 --bind-to none \
  sh -c '
    unset LD_PRELOAD NCCL_PROFILER_PLUGIN NCCL_PROFILE_EVENT_MASK NCCL_PROFILE_DUMP_FILE
    if [ "$G002_MODE" = plugin ]; then
      export NCCL_PROFILER_PLUGIN="$G002_PLUGIN" NCCL_PROFILE_EVENT_MASK=64
      export NCCL_PROFILE_GROUP_POOL_SIZE=128 NCCL_PROFILE_COLL_POOL_SIZE=128
      export NCCL_PROFILE_DUMP_FILE="$G002_OUTPUT/trace"
    fi
    exec /usr/bin/time -v -o "$G002_OUTPUT/rss-$OMPI_COMM_WORLD_RANK.txt" \
      env NCCL_DEBUG=INFO NCCL_DEBUG_FILE="$G002_OUTPUT/nccl.%p.log" \
      LD_DEBUG=libs LD_DEBUG_OUTPUT="$G002_OUTPUT/loader" \
      "$G002_BINARY" -b 8M -e 8M -g 1 -n "$G002_ITERS" -w "$G002_WARMUP" -c 0 -z 0 \
      -J "$G002_OUTPUT/result-$OMPI_COMM_WORLD_RANK.json"
  ' > "$G002_OUTPUT/stdout.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$G002_OUTPUT/exit-code.txt"
exit "$rc"
