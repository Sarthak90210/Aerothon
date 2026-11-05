#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_DOMAIN_ID=42 ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ros2 topic list 2>/dev/null | grep -i "pose\|map\|slam" 
echo ---; ros2 topic info -v /pose 2>/dev/null | grep -E "Node name|Reliability|Durability|Publisher count|Subscription count"
echo ---; timeout 5 ros2 topic echo /pose --once 2>&1 | head -5
