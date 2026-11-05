#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/sim:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest sim/test_search_current_command.py -q
