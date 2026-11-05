#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=222 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_regressions_20261007.py > logs/reliability_tracking_margin_trials_owned_20261007/regressions.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/run_tracking_margin_batch_20261007.py
