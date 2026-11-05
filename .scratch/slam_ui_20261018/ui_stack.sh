#!/usr/bin/env bash
set -e
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
here="$repo/.scratch/slam_ui_20261018"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=77 FASTDDS_BUILTIN_TRANSPORTS=SHM
export AEROTHON_GCS_WS_PORT=8777 AEROTHON_MAP_ONLINE=0
export ARENA_W=40 ARENA_H=30 MAP_PERIOD=1
export PYTHONPATH="$repo/src/aerothon_gcs/gcs_aggregator:$repo/src/aerothon_mission/mission_bt:$repo/src/aerothon_perception/perception_banner:$repo/src/aerothon_runtime:${PYTHONPATH:-}"
mkdir -p "$here/ui_state"
cp "$repo/.scratch/gcs_testing_20261018/state/profiles.json" "$here/ui_state/profiles.json"
pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true; wait || true' EXIT
trap 'exit 0' INT TERM
python3 "$here/controlled_vehicle.py" > "$here/ui_vehicle.log" 2>&1 & pids+=($!)
python3 -m gcs_aggregator.aggregator --ros-args -p managed:=true -p ws_host:=127.0.0.1 -p dimension_presets_file:="$here/ui_state/presets.json" > "$here/ui_aggregator.log" 2>&1 & pids+=($!)
python3 "$here/ui_web.py" "$repo/src/aerothon_gcs/tauri_app/dist" "$here/ui_state" > "$here/ui_web.log" 2>&1 & pids+=($!)
printf '%s\n' "${pids[@]}" > "$here/ui_pids"
wait
