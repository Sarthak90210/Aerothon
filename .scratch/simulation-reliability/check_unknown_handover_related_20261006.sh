#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=220
export PYTHONPATH="$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_avoidance/avoidance:$PWD/src/aerothon_payload/winch_ctrl:$PWD/src/aerothon_perception/camera_ctrl:$PWD/src/aerothon_perception/perception_qr:$PWD/src/aerothon_perception/perception_redzone:$PWD/src/aerothon_perception/perception_banner:${PYTHONPATH:-}"
python3 -m pytest sim/test_fcu_velocity_sample_alignment.py sim/test_velocity_command_delay.py sim/test_yaw_motion_certification.py sim/test_corridor_clearance_contract.py sim/test_fcu_navigation_velocity.py -q
