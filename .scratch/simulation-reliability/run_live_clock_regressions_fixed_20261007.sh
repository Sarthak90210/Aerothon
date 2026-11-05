#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/check_live_clock_controller_candidate_20261007.py > logs/reliability_live_clock_controller_regressions_fixed_20261007.log 2>&1
