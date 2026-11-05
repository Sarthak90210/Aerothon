#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1
timeout 15 ros2 topic hz /mavros/home_position/home 2>&1 | tail -3
timeout 10 ros2 topic hz /mavros/state 2>&1 | tail -2
