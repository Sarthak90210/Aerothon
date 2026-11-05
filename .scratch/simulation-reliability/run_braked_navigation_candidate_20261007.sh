#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=228 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/braked_navigation_candidate_20261007/sim/run_braked_navigation_probe.py
