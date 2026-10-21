#!/usr/bin/env bash
# No GPU use. Explicit, distinct role addresses; run in a NEW private directory.
# Usage: g1_04_sidecar.sh client|server TASK_DIR RUN EPOCH
set -euo pipefail
role=${1:?client/server}
task_dir=${2:?private task directory}
run_id=${3:?run}
epoch=${4:?epoch}
: "${DDP_MASTER_ADDR:?reference rendezvous address}"
: "${CONTROL_SOURCE_ADDR:?source node listen and client destination address}"
: "${CONTROL_PORT:?independent control port}"
[[ "$role" = client || "$role" = server ]]
[[ "$run_id" =~ ^[A-Za-z0-9_-]+$ && "$epoch" =~ ^[A-Za-z0-9_-]+$ ]]
cd "$task_dir"
umask 077
ulimit -f 65536
./venv/bin/python g1_04_preflight.py config --ddp-master-addr "$DDP_MASTER_ADDR" --control-source-addr "$CONTROL_SOURCE_ADDR"
# Never overwrite a prior or interrupted session.
for file in control.json ready.json control-exit.txt sidecar.pid; do test ! -e "$file"; done
node=node-a; peer=node-b
[[ "$role" = client ]] || { node=node-b; peer=node-a; }
set +e
nice -n 5 timeout --signal=TERM --kill-after=3s 115s ./venv/bin/python g1_04_control.py "$role" \
  --address "$CONTROL_SOURCE_ADDR" --port "$CONTROL_PORT" --run "$run_id" --epoch "$epoch" \
  --node "$node" --expected-peer-node "$peer" --ready-output ready.json \
  --duration "${CONTROL_DURATION_S:-90}" --count 120000 --interval 0.0005 \
  --timeout "${CONTROL_TIMEOUT_S:-110}" --output control.json > control.log 2>&1 &
pid=$!
printf '%s\n' "$pid" > sidecar.pid
wait "$pid"
rc=$?
printf '%s\n' "$rc" > control-exit.txt
exit "$rc"
