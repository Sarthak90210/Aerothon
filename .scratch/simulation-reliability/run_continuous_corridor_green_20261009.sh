#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/sim:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/scripts:${PYTHONPATH:-}"
python3 -m pytest sim/test_continuous_corridor_certificate.py sim/test_local_planner.py sim/test_corridor_clearance_contract.py sim/test_changing_disturbance_certification.py -q -s > logs/reliability_v39_continuous_certificate_focused_20261009.log 2>&1
