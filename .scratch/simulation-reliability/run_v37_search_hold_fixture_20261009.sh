#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest .scratch/simulation-reliability/test_search_current_command_safe_fixture_20261009.py -q -s > logs/reliability_v37_search_hold_fixture_probe_20261009.log 2>&1
