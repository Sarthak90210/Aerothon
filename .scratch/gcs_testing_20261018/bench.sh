#!/usr/bin/env bash
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$repo/src/aerothon_mission/mission_bt:$repo/src/aerothon_perception/perception_banner:$PYTHONPATH"
/usr/bin/python3 "$repo/.scratch/gcs_testing_20261018/bench_map.py"
