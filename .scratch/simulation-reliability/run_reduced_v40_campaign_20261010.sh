#!/usr/bin/env bash
# The 96 eligible reduced-campaign navigation flights on the V40 freeze.
# Workers are independent ROS domains at real-time speed; the count stays low
# enough that the controller's own 0.20 s computation budget and capture-gap
# guards measure the aircraft rather than host contention.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PYTHONNOUSERSITE=1
workers="${AEROTHON_CAMPAIGN_WORKERS:-4}"
/usr/bin/python3 sim/run_navigation_campaign.py --reduced-no-strong-or-delay -j "$workers" --rtf 1 \
 --out logs/reliability_reduced_v40_campaign_20261010 \
 --targeted logs/reliability_reduced_v40_render_my_world_s20261003_20261010 \
            logs/reliability_reduced_v40_render_my_world_s1001_20261010 \
            logs/reliability_reduced_v40_render_shipped_s20261003_20261010 \
            logs/reliability_reduced_v40_render_rb_rotated_s20261003_20261010 \
            logs/reliability_reduced_v40_render_split_corridors_s20261003_20261010
