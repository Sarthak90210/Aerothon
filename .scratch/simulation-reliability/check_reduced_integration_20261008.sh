#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/perception_qr:$PWD/sim:$PYTHONPATH"
export ROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 PYTHONNOUSERSITE=1
/usr/bin/python3 -m pytest -q sim/test_native_contact_evidence.py sim/test_vehicle_contact_sensors.py sim/test_gate_braking.py sim/test_search_braking_20261007.py sim/test_campaign_contact_evidence.py sim/test_return_gate_search.py sim/test_navigation_campaign_gate.py sim/test_reduced_qualification_scope.py sim/test_return_fine_framing.py sim/test_return_clipped_framing.py sim/test_command_computation_deadline.py sim/test_banner_capture_contract.py
