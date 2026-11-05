#!/usr/bin/env bash
# Pi half: the real web host; Connect starts the production runtime (domain 42).
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
here="$repo/.scratch/gcs_testing_20261018"
cd "$repo"
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_DOMAIN_ID=42
export AEROTHON_DEVICE_STATE_DIR="$here/sitl_device_state"
export PYTHONPATH="$repo/src/aerothon_runtime:${PYTHONPATH:-}"
export AEROTHON_MAP_ONLINE=0
mkdir -p "$here/sitl_state" "$AEROTHON_DEVICE_STATE_DIR"
[ -e "$here/sitl_state/map-tiles" ] || ln -s ../../india_map_20261018/tiles "$here/sitl_state/map-tiles"
exec /usr/bin/python3 -m aerothon_runtime.web --static src/aerothon_gcs/tauri_app/dist \
  --state-dir "$here/sitl_state" --bind 127.0.0.1 --port 8897
