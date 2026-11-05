#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1
python3 -m pytest sim/test_detector_timing.py sim/test_leg_routing.py sim/test_search_planner.py sim/test_corridor_recovery.py sim/test_frame_conventions.py sim/test_corridor_yaw_alignment.py sim/test_navigator_equivalence.py sim/test_local_planner.py sim/test_corridor_clearance_contract.py -q > logs/reliability_targeted.log 2>&1