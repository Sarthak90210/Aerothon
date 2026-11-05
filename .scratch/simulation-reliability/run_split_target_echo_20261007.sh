#!/usr/bin/env bash
set -uo pipefail
set +u
source install/setup.bash
set -u
export ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1 PYTHONNOUSERSITE=1
out=logs/reliability_render_split_return_fcu_echo_20261007
[[ ! -e "$out" ]] || exit 2
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_ENTRY="$PWD/.scratch/simulation-reliability/split_return_entry_20261007.json"
export AEROTHON_CORRIDOR_HANDOVER=stationary
export AEROTHON_MOTION_FORECAST_OUT="$PWD/$out/motion_forecasts.json"
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "$out" logs/delivery_profile_20261005.json > "${out}_launcher.log" 2>&1 & runner=$!
/usr/bin/python3 .scratch/simulation-reliability/record_fcu_target_echo_20261007.py --out "$out" > "${out}_target_echo.log" 2>&1 & observer=$!
trap 'kill -TERM "$observer" 2>/dev/null || true' EXIT
wait "$runner";status=$?
wait "$observer" || true
exit "$status"
