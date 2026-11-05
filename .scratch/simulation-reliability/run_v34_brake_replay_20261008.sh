#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest .scratch/simulation-reliability/test_v34_brake_physics_seam_20261008.py -q -s > logs/reliability_v34_brake_physics_red_20261008.log 2>&1
