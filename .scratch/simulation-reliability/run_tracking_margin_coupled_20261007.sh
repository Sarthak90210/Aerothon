#!/usr/bin/env bash
set -eo pipefail
source install/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=221 ROS_LOCALHOST_ONLY=1
/usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_contract_20261007.py > logs/reliability_tracking_margin_coupled_owned_20261007/contract.log 2>&1
exec /usr/bin/python3 .scratch/simulation-reliability/check_tracking_margin_coupled_20261007.py
