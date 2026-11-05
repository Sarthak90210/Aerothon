#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/sim:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest sim/test_search_current_command.py sim/test_search_braking_20261007.py sim/test_search_escape_lookahead.py sim/test_leg_routing.py sim/test_search_planner.py -q
