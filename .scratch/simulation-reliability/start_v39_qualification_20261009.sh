#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
python3 -u .scratch/simulation-reliability/run_v39_qualification_gates_20261008.py > logs/reliability_v39_qualification_pipeline_20261009.log 2>&1
