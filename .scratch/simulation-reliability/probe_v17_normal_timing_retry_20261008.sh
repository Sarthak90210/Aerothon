#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PYTHONNOUSERSITE=1
python3 .scratch/simulation-reliability/probe_v17_normal_timing_retry_20261008.py
