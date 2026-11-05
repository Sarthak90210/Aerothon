#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/sim:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest sim/test_return_vertical_framing.py sim/test_return_fine_framing.py sim/test_return_clipped_framing.py sim/test_return_gate_search.py sim/test_native_contact_evidence.py sim/test_vehicle_contact_sensors.py -q
