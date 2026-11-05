#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1
export ROS_DOMAIN_ID=214
python3 -m pytest sim/test_slalom_traverse.py sim/test_corridor_stress.py -q > logs/corridor_strict_stress.log 2>&1