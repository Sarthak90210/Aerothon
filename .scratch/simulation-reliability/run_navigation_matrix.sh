#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1
python3 sim/run_navigation_campaign.py \
  --targeted logs/reliability_render_my_world_s20261003_bannerfix_20261006 \
             logs/reliability_render_my_world_s1001_bannerfix_20261006 \
  --out logs/reliability_navigation_matrix_20261006 -j 6 --rtf 4
