#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=216
python3 -m pytest sim/test_altitude_hold.py sim/test_fail_closed_stages.py sim/test_slalom_traverse.py -q > logs/reliability_iteration.log 2>&1
