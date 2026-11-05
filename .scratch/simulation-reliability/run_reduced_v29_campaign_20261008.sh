#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PYTHONNOUSERSITE=1
/usr/bin/python3 sim/run_navigation_campaign.py --reduced-no-strong-or-delay -j 2 --rtf 2 --out logs/reliability_reduced_v29_campaign_20261008 --targeted logs/reliability_reduced_v29_render_my_world_s20261003_20261008 logs/reliability_reduced_v29_render_my_world_s1001_20261008 logs/reliability_reduced_v29_render_shipped_s20261003_20261008 logs/reliability_reduced_v29_render_rb_rotated_s20261003_20261008 logs/reliability_reduced_v29_render_split_corridors_s20261003_20261008
