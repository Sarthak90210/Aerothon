#!/usr/bin/env bash
set -e
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD:$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_avoidance/avoidance:$PYTHONPATH"
/usr/bin/python3 -c 'import sys,rclpy,pytest; print(sys.version, rclpy.__file__)'
/usr/bin/python3 -m pytest sim/test_gcs_aggregator.py sim/test_arena_dimensions.py sim/test_gcs_merge_contract.py sim/test_lidar_calibration_gcs.py -q --tb=short > .scratch/gcs_merge_20261014/focused.log 2>&1
tail -45 .scratch/gcs_merge_20261014/focused.log
