#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="$PWD:$PWD/src/aerothon_gcs/gcs_aggregator:$PWD/src/aerothon_mission/mission_bt:$PWD/src/aerothon_perception/perception_banner:$PWD/src/aerothon_perception/camera_ctrl:$PYTHONPATH"
/usr/bin/python3 -m cProfile -o .scratch/gcs_merge_20261014/performance.pstats .scratch/gcs_merge_20261014/performance_probe.py > .scratch/gcs_merge_20261014/performance-profile.log 2>&1
/usr/bin/python3 - <<'PY'
import pstats
pstats.Stats('.scratch/gcs_merge_20261014/performance.pstats').strip_dirs().sort_stats('cumulative').print_stats('banner_node|letter|tesseract|cv_bridge|templat', 22)
PY
