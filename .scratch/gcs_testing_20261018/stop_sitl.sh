#!/usr/bin/env bash
# Aircraft confirmed disarmed on the ground in the GCS before this runs.
pkill -f sitl_pi_loop.sh
for p in $(pgrep -f "aerothon_runtime.web --static"); do kill "$p"; done
for g in $(ps -eo pgid,args | grep "mission2.launch.py" | grep -v grep | awk '{print $1}' | sort -u); do kill -INT -- "-$g"; done
pg=$(cat /tmp/aerothon_stack.pgid 2>/dev/null); [ -n "$pg" ] && kill -INT -- "-$pg"
sleep 10
ps -eo pid,args | grep -E "arducopter|gz sim|mission2.launch|aerothon_runtime.web|execution_node|gcs_aggregator" | grep -v grep | cut -c1-90 || true
echo done
