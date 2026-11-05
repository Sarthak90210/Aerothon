#!/usr/bin/env bash
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$repo/src/aerothon_gcs/gcs_aggregator:$repo/src/aerothon_mission/mission_bt:$repo/src/aerothon_perception/perception_banner:$repo/src/aerothon_runtime:$PYTHONPATH"
cd "$repo"
/usr/bin/python3 -m pytest -q -p no:cacheprovider "$@" 2>&1 | tail -15
