#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
out=${1:-logs/pi_gateway_shipped_s20261003_20261014}
test ! -e "$out" || { echo 'Fresh evidence directory required'; exit 1; }
mkdir -p "$out"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export AEROTHON_GATEWAY_PYTHON="$PWD/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
export AEROTHON_GATEWAY_PORT=19090 AEROTHON_GATEWAY_MAVLINK_PORT=5762
export AEROTHON_WORLD_SPEC="$PWD/sim/worlds/shipped.json"
export AEROTHON_CONDITIONS=calm AEROTHON_CONDITIONS_SEED=20261003 AEROTHON_SEED=20261003
export AEROTHON_HEADLESS=1 AEROTHON_OPEN_GCS=0 AEROTHON_NO_REAP=1
export AEROTHON_AIRFRAME=cad AEROTHON_PAYLOAD_FIXTURE=loaded
export AEROTHON_CAMERA_W=1280 AEROTHON_CAMERA_H=720
export AEROTHON_GUI_CLEANUP=0
cp .scratch/pi_remote_runtime_20261014/runtime6.zip "$out/frozen_pi_runtime.zip"
cp logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013/frozen_calibration.json "$out/frozen_calibration.json"
exec bash scripts/launch_laptop_sim.sh >"$out/stack.log" 2>&1
