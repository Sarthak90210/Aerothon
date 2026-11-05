#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/sim:${PYTHONPATH:-}"
/usr/bin/python3 -m pytest sim/test_return_sweep_efficiency.py sim/test_first_return_level_view.py sim/test_return_inherited_tilt.py sim/test_banner_sweep.py sim/test_banner_orbit.py sim/test_fail_closed_stages.py sim/test_gate_braking.py sim/test_return_vertical_framing.py sim/test_return_fine_framing.py sim/test_return_clipped_framing.py sim/test_return_gate_search.py sim/test_native_contact_evidence.py sim/test_vehicle_contact_sensors.py -q
