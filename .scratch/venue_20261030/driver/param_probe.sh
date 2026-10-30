#!/bin/bash
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"
set +u; source /opt/ros/jazzy/setup.bash; source install/setup.bash; set -u
export ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_DOMAIN_ID=42
ros2 service list --no-daemon 2>/dev/null | grep -i "mavros/param" | head
timeout 20 ros2 service call /mavros/param/get_parameters rcl_interfaces/srv/GetParameters "{names: ['WINCH_RATE_MAX','WINCH_TYPE']}" 2>/dev/null | tail -3
