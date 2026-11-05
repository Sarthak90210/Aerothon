#!/bin/bash
# Laptop side of laptop-simulation mode for the Pi at 192.168.0.102:
# Gazebo, SITL, device bridges and gateway only (mission_stack:=false).
set -eo pipefail
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
out=logs/pi_deploy_laptop_sim_20261015
test ! -e "$out" || { echo 'Fresh evidence directory required'; exit 1; }
mkdir -p "$out"
set +u; source /opt/ros/jazzy/setup.bash; source "$HOME/aerothon_stack/install/setup.bash"; source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_WORLD_SPEC="$PWD/sim/worlds/clarified_h115_both.json" AEROTHON_CONDITIONS=calm AEROTHON_CONDITIONS_SEED=20261003 AEROTHON_SEED=20261003
export AEROTHON_HEADLESS=1 AEROTHON_OPEN_GCS=0 AEROTHON_AIRFRAME=cad AEROTHON_PAYLOAD_FIXTURE=loaded
export AEROTHON_GATEWAY_PYTHON="$PWD/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
# Windows reserves TCP 8075-8174, so the sensor gateway uses 19090 end to end.
export AEROTHON_GATEWAY_PORT=19090 AEROTHON_GATEWAY_MAVLINK_PORT=5762
export PYTHONPATH="$PWD/src/aerothon_runtime:${PYTHONPATH:-}"
git rev-parse HEAD > "$out/git_head.txt"; git status --short > "$out/git_status.txt"
exec bash scripts/launch_laptop_sim.sh > "$out/stack.log" 2>&1
