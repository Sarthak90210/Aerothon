#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
export PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1
out="$1"
shift
exec /usr/bin/python3 .scratch/simulation-reliability/audit_decision_inputs.py "$out/decision_inputs.json" "$@"
