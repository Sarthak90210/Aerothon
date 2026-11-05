#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1
python3 -m pytest sim/test_local_planner.py sim/test_corridor_clearance_contract.py sim/test_slalom_traverse.py sim/test_corridor_stress.py sim/test_velocity_command_delay.py sim/test_changing_disturbance_certification.py sim/test_yaw_motion_certification.py -q
colcon build --paths src/aerothon_avoidance/avoidance src/aerothon_mission/mission_bt src/aerothon_perception/perception_qr src/aerothon_perception/perception_redzone --symlink-install --packages-select avoidance mission_bt perception_qr perception_redzone
