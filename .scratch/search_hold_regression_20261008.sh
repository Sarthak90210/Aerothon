#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=20
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/sim:${PYTHONPATH:-}"
python3 -m pytest sim/test_search_current_command.py sim/test_search_braking_20261007.py sim/test_leg_routing.py sim/test_detector_timing.py sim/test_decode_hover.py sim/test_headless_sensor_cadence.py sim/test_headless_world.py sim/test_headless_command_delay.py sim/test_headless_observation_contract.py sim/test_return_capture_batching.py sim/test_banner_capture_contract.py -q
