#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export PYTHONNOUSERSITE=1
/usr/bin/python3 .scratch/simulation-reliability/probe_reduced_targeted_v40_20261010.py
