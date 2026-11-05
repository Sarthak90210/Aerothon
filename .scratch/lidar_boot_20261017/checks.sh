#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source "$PWD/install/setup.bash"
source "$PWD/.scratch/lidar_boot_20261017/colcon_install/local_setup.bash"
export PYTHONPATH="$PWD/src/aerothon_runtime:$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_mission/mission_bringup:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_banner:$PWD/sim:${PYTHONPATH:-}"
exec /usr/bin/python3 -m pytest "$@"
