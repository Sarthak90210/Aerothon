#!/usr/bin/env bash
set -e
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD/src/aerothon_runtime:${PYTHONPATH:-}"
exec .scratch/pi_remote_runtime_20261014/testenv/bin/python .scratch/pi_remote_runtime_20261014/record_camera.py logs/pi_gateway_shipped_s20261003_onboardfix_20261014
