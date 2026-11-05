#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
colcon build --symlink-install --packages-select avoidance > logs/reliability_v39_build_20261009.log 2>&1
source install/setup.bash
python3 .scratch/simulation-reliability/verify_reduced_v39_startup_20261008.py > logs/reliability_v39_startup_verify_20261009.log 2>&1
