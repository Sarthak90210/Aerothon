#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
/usr/bin/python3 .scratch/slam_ui_20261018/wait_sitl_disarm.py
exec /usr/bin/python3 .scratch/slam_ui_20261018/local_sitl_probe.py command 300 \
  @.scratch/slam_ui_20261018/task_delivery_gps.json delivery_gps
