#!/usr/bin/env bash
# Run only on the two authorized test nodes. Private task dir/venv must exist.
# Usage: g1_03_run.sh MODE TASK_DIR NODE_RANK MASTER_ADDR RUN_ID RANK_EPOCH
# MODE=baseline|plugin. Start both multinode launchers together.
set -euo pipefail
mode=${1:?smoke/baseline/plugin}
task_dir=${2:?private task directory}
node_rank=${3:?0/1}
master_addr=${4:?rendezvous address}
run_id=${5:?run alias}
rank_epoch=${6:?fresh epoch per invocation}
[[ "$node_rank" = 0 || "$node_rank" = 1 ]]
[[ "$run_id" =~ ^[A-Za-z0-9_-]+$ && "$rank_epoch" =~ ^[A-Za-z0-9_-]+$ ]]
[[ "${CUDA_VISIBLE_DEVICES:?expose two authorized H800 GPUs}" =~ ^[0-9]+,[0-9]+$ ]]
cd "$task_dir"
task_dir=$PWD
export OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset NCCL_MIN_NRINGS NCCL_MAX_NRINGS
export NCCL_MIN_NCHANNELS=1 NCCL_MAX_NCHANNELS=32
export NCCL_MIN_CTAS=1 NCCL_MAX_CTAS=32 NCCL_NVLS_NCHANNELS=16 NCCL_DEBUG=INFO
# The pinned isolated v4 example has MAX_CHANNELS=32. Apply the same cap
# to baseline and capture. No diagnostic collectives or per-step sync.
unset LD_PRELOAD NCCL_PROFILE_EVENT_MASK NCCL_PROFILE_DUMP_FILE
export G103_RUN_ID="$run_id" G103_EPOCH="$rank_epoch"
export G103_NODE=node-a
[[ "$node_rank" = 0 ]] || export G103_NODE=node-b
export NCCL_PROFILER_PLUGIN=none
test ! -e "$mode"  # Reject even interrupted runs; never mix stale evidence.
mkdir "$mode"
export NCCL_DEBUG_FILE="$task_dir/$mode/nccl.%p.log"
if [[ "$mode" = plugin ]]; then
  export NCCL_PROFILER_PLUGIN="$task_dir/nccl-v2.27.7-1/ext-profiler/example/libnccl-profiler-example.so"
  test -r "$NCCL_PROFILER_PLUGIN"
  export NCCL_PROFILE_EVENT_MASK=66
  export NCCL_PROFILE_GROUP_POOL_SIZE=128 NCCL_PROFILE_COLL_POOL_SIZE=128
  export NCCL_PROFILE_P2P_POOL_SIZE=1 NCCL_PROFILE_PROXY_CTRL_POOL_SIZE=1
  export NCCL_PROFILE_PROXY_DETACH_POOL_SIZE=1
  export NCCL_PROFILE_DUMP_FILE="$task_dir/$mode/trace"
  test -w "$task_dir/$mode"
fi
case "$mode" in
  baseline|plugin) nodes=2; capture_mode=multinode; warmup=5; steps=30 ;;
  *) exit 2 ;;
esac
node_alias=node-a
[[ "$node_rank" = 0 ]] || node_alias=node-b
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv,noheader > "$mode/gpu-before.txt"
set +e
timeout --signal=TERM --kill-after=10s 180s "$task_dir/venv/bin/python" \
  -m torch.distributed.run --nnodes="$nodes" --nproc-per-node=2 \
  --node-rank="$node_rank" --master-addr="$master_addr" --master-port="${G103_MASTER_PORT:-29629}" \
  "$task_dir/g1_01_ddp_capture.py" --mode "$capture_mode" --node-alias "$node_alias" \
  --run-id "$run_id" --rank-epoch "$rank_epoch" --warmup "$warmup" --steps "$steps" \
  --output "$task_dir/$mode" > "$mode/stdout.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$mode/exit-code.txt"
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv,noheader > "$mode/gpu-after.txt"
exit "$rc"
