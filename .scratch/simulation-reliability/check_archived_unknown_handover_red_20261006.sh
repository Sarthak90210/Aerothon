#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=220
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/src/aerothon_perception/perception_banner:${PYTHONPATH:-}"
python3 .scratch/simulation-reliability/run_archived_unknown_handover_red_20261006.py logs/reliability_render_return_measurement_time_moving_20261006/recorded_source.zip
