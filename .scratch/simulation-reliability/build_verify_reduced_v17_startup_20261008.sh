#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
colcon build --base-paths src/aerothon_mission/mission_bt src/aerothon_avoidance/avoidance --packages-select mission_bt avoidance --symlink-install
source install/setup.bash
/usr/bin/python3 .scratch/simulation-reliability/verify_reduced_v17_startup_20261008.py
