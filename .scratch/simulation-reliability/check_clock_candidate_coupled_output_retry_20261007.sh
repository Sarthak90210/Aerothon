#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=225 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/check_clock_candidate_coupled_valid_domain_20261007.py > logs/reliability_clock_candidate_coupled_output_retry_20261007.log 2>&1
