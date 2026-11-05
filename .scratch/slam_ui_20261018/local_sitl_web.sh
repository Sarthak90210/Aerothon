#!/usr/bin/env bash
set -eo pipefail
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
cd "$repo"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export AEROTHON_DEVICE_STATE_DIR="$repo/.scratch/slam_ui_20261018/local_sitl_devices"
export PYTHONPATH="$repo/src/aerothon_runtime:${PYTHONPATH:-}"
export AEROTHON_MAP_ONLINE=0
state="$repo/.scratch/slam_ui_20261018/local_sitl_state"
mkdir -p "$state" "$AEROTHON_DEVICE_STATE_DIR"
if [ ! -f "$state/profiles.json" ]; then
    cp .scratch/gcs_testing_20261018/sitl_state/profiles.json "$state/profiles.json"
fi
exec /usr/bin/python3 -m aerothon_runtime.web --static src/aerothon_gcs/tauri_app/dist \
  --state-dir "$state" --bind 127.0.0.1 --port 8897
