#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/probe_observed_corridor_bootstrap_20261007.py > logs/reliability_observed_corridor_bootstrap_20261007.log 2>&1
