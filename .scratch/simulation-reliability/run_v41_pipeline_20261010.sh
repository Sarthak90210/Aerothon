#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
exec python3 -u .scratch/simulation-reliability/run_v41_qualification_gates_20261010.py
