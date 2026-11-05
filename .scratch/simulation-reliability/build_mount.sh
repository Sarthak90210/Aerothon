#!/usr/bin/env bash
set -euo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1
colcon build --paths src/aerothon_avoidance/avoidance src/aerothon_mission/mission_bt src/aerothon_perception/perception_qr src/aerothon_perception/perception_redzone --symlink-install --packages-select avoidance mission_bt perception_qr perception_redzone
