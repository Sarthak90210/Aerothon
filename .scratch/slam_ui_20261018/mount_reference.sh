#!/usr/bin/env bash
set -e
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$repo/src/aerothon_mission/mission_bringup:${PYTHONPATH:-}"
python3 "$repo/.scratch/slam_ui_20261018/mount_reference.py"
