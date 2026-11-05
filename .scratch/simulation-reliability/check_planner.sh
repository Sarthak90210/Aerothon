#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1
python3 -m pytest sim/test_local_planner.py sim/test_corridor_recovery.py sim/test_corridor_yaw_alignment.py sim/test_slalom_traverse.py sim/test_corridor_stress.py -q > logs/corridor_planner_first_tests.log 2>&1