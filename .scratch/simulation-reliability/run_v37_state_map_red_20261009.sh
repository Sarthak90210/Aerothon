#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest sim/test_behavior_tree.py::TestMissionBT::test_every_mission_leaf_has_a_gcs_state_name -q > logs/reliability_v37_state_map_red_20261009.log 2>&1
