#!/usr/bin/env bash
set -eo pipefail
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
cd "$repo"
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export AEROTHON_HEADLESS=1
export AEROTHON_CAMERA_W=640 AEROTHON_CAMERA_H=360
export AEROTHON_CONDITIONS=calm
export AEROTHON_GATEWAY_PYTHON="$repo/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
export PYTHONPATH="$repo/src/aerothon_runtime:${PYTHONPATH:-}"
exec bash scripts/launch_laptop_sim.sh
