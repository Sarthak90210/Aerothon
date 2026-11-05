#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/run_focused_clock_navigation_20261007.py
