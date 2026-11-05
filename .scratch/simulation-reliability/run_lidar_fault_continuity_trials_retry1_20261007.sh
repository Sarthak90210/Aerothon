#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=224 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_lidar_fault_continuity_regressions_20261007.py > logs/reliability_lidar_fault_continuity_trials_retry1_owned_20261007/regressions.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/run_lidar_fault_continuity_batch_20261007.py
