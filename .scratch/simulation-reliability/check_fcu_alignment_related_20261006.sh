#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1
python3 -m pytest sim/test_fcu_velocity_sample_alignment.py sim/test_fcu_navigation_velocity.py sim/test_velocity_command_delay.py sim/test_yaw_motion_certification.py sim/test_corridor_clearance_contract.py -q
