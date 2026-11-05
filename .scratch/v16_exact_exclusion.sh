#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=20
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/sim:${PYTHONPATH:-}"
python3 -m pytest sim/test_observed_exclusion_certificate.py -q 2>&1 | tee logs/reliability_v16_exact_exclusion_red_20261008.log
