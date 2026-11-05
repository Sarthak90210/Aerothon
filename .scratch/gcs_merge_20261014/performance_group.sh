#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD:$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/camera_ctrl:$PYTHONPATH"
/usr/bin/python3 -m pytest sim/test_banner_identity.py::ShadowRobustLetteringTests -q --tb=short --durations=1 > .scratch/gcs_merge_20261014/performance-group.log 2>&1
rc=$?
cat .scratch/gcs_merge_20261014/performance-group.log
exit "$rc"
