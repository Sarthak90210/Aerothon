#!/usr/bin/env bash
set +u; source /opt/ros/jazzy/setup.bash
export FASTDDS_BUILTIN_TRANSPORTS=SHM ROS_DOMAIN_ID=77; unset ROS_LOCALHOST_ONLY
ros2 topic info /pose --no-daemon; ros2 topic info /map --no-daemon
timeout 6 ros2 topic hz /map --no-daemon 2>&1 | tail -3
