#!/usr/bin/env bash
set -euo pipefail
domain="${1:?Pass the actual SITL ROS domain first}"; shift
[[ "$domain" =~ ^[0-9]+$ && "$domain" -le 232 ]] || { echo 'Invalid ROS domain'; exit 2; }
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID="$domain" ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/collect_guided_options_ros2_20261007.py "$@"
