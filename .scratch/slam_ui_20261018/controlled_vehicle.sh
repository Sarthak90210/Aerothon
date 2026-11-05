#!/usr/bin/env bash
set -e
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=77 FASTDDS_BUILTIN_TRANSPORTS=SHM
export ARENA_W=40 ARENA_H=30 MAP_PERIOD=1
exec python3 "$repo/.scratch/slam_ui_20261018/controlled_vehicle.py"
