#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_combined_observation_regressions_20261007.py > logs/reliability_combined_observation_checks_owned_20261007/regressions.log 2>&1
/usr/bin/python3 .scratch/simulation-reliability/check_combined_gate_pause_20261007.py
exec /usr/bin/python3 .scratch/simulation-reliability/run_combined_observation_batch_20261007.py
