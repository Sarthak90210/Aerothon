#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=217
python3 -m pytest sim/test_detector_timing.py sim/test_observation_registration.py sim/test_leg_routing.py sim/test_search_planner.py sim/test_corridor_recovery.py sim/test_frame_conventions.py sim/test_corridor_yaw_alignment.py sim/test_navigator_equivalence.py sim/test_local_planner.py sim/test_corridor_clearance_contract.py sim/test_altitude_hold.py sim/test_fail_closed_stages.py -q > logs/reliability_targeted_final.log 2>&1
colcon build --base-paths src --symlink-install --packages-select avoidance mission_bt perception_qr perception_redzone > logs/reliability_build.log 2>&1
