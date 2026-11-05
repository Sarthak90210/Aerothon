#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=225 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/trace_coupled_forecasts_20261007.py
