#!/usr/bin/env bash
set -e
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_perception/perception_banner:$PYTHONPATH"
/usr/bin/python3 .scratch/gcs_merge_20261014/ros_websocket_check.py > .scratch/gcs_merge_20261014/ros-websocket.log 2>&1
tail -25 .scratch/gcs_merge_20261014/ros-websocket.log
