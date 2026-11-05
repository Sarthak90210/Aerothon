#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=228 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/motion_forecast_candidate_20261007/sim/run_braked_navigation_probe.py
