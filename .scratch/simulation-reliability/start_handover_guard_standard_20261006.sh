#!/usr/bin/env bash
set -euo pipefail
seed="${1:?standard seed}"
case "$seed" in 20261003|1001) ;; *) echo 'Unexpected acceptance seed'; exit 2 ;; esac
export AEROTHON_RENDER_TRIAL=mission
unset AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER
out="logs/reliability_render_my_world_s${seed}_handover_guard_20261006"
runner_rc=0
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json "$seed" "$out" logs/delivery_profile_20261005.json || runner_rc=$?
/usr/bin/python3 .scratch/simulation-reliability/archive_recorded_source.py "$out"
exit "$runner_rc"
