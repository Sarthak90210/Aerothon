#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1
timeout 45 ros2 topic echo /camera/pose_state --once
