#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
bash .scratch/simulation-reliability/check_reduced_integration_20261008.sh > logs/reliability_reduced_final_components_retry_20261008.log 2>&1
/usr/bin/python3 .scratch/simulation-reliability/freeze_reduced_scope_20261008.py > logs/reliability_reduced_scope_freeze_20261008.log 2>&1
/usr/bin/python3 -u .scratch/simulation-reliability/run_reduced_seed_trials_20261008.py > logs/reliability_reduced_seed_trials_launcher_20261008.log 2>&1
