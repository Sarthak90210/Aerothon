#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/sim:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest sim/test_motion_certificate_batching.py sim/test_command_computation_deadline.py sim/test_local_planner.py sim/test_corridor_clearance_contract.py sim/test_velocity_command_delay.py sim/test_corridor_stress.py -q
