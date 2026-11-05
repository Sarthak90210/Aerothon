#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest sim/test_gate_braking.py sim/test_gate_motion_physics.py sim/test_gate_brake_motion_anchor.py sim/test_gate_capture_pause.py -q -s > logs/reliability_v35_gate_braking_focused_20261008.log 2>&1
