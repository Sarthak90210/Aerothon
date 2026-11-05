#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=223 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/check_motion_forecast_trace_20261007.py
