#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219 ROS_LOCALHOST_ONLY=1
python3 .scratch/simulation-reliability/run_archived_velocity_alignment_red_20261006.py logs/reliability_render_my_world_s20261003_bannerfix_20261006/recorded_source.zip
