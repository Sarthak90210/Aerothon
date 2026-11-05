#!/usr/bin/env bash
set -eo pipefail
# This setup already chains both /opt/ros/jazzy and aerothon_stack/install.
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=225 ROS_LOCALHOST_ONLY=1
exec /usr/bin/python3 .scratch/simulation-reliability/check_clock_candidate_coupled_20261007.py > logs/reliability_clock_candidate_coupled_valid_domain_20261007.log 2>&1
