#!/usr/bin/env bash
set -euo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1
python3 -m pytest sim/test_lidar_registration.py sim/test_scan_geometry.py sim/test_observation_registration.py sim/test_local_planner.py sim/test_corridor_clearance_contract.py "$@" -q
