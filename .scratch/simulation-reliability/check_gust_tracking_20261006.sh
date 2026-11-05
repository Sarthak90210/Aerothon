#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=223 ROS_LOCALHOST_ONLY=1
python3 .scratch/simulation-reliability/probe_gust_tracking_20261006.py "$@"
