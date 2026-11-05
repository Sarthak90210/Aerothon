#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_DOMAIN_ID=43 ROS_LOCALHOST_ONLY=1
timeout 8 ros2 topic hz /joint_states 2>&1 | tail -4
timeout 6 ros2 topic hz /clock 2>&1 | tail -2
