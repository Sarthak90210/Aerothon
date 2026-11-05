#!/usr/bin/env bash
# Laptop half of the laptop-simulation route: Gazebo, SITL, device gateway.
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
cd "$repo"
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export AEROTHON_HEADLESS=1
# Closed-loop runs on this laptop: the master guide recommends a low render size.
export AEROTHON_CAMERA_W=${AEROTHON_CAMERA_W:-960} AEROTHON_CAMERA_H=${AEROTHON_CAMERA_H:-540}
export AEROTHON_GATEWAY_PYTHON="$repo/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
export PYTHONPATH="$repo/src/aerothon_runtime:${PYTHONPATH:-}"
exec bash scripts/launch_laptop_sim.sh
