#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source .scratch/pi_remote_runtime_20261014/testenv/bin/activate
export PYTHONPATH="$PWD/src/aerothon_runtime:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_avoidance/avoidance:${PYTHONPATH:-}"
python -m pytest tests/test_pi_runtime.py verification/test_pi_ros_runtime.py -q --tb=short >.scratch/pi_remote_runtime_20261014/focused4.log 2>&1
rc=$?
tail -n 65 .scratch/pi_remote_runtime_20261014/focused4.log
exit "$rc"
