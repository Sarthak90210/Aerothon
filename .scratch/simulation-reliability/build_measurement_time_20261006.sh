#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1
colcon build --paths src/aerothon_avoidance/avoidance --symlink-install --packages-select avoidance
