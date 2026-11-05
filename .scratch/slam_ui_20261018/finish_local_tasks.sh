#!/usr/bin/env bash
set -eo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
here=.scratch/slam_ui_20261018
/usr/bin/python3 "$here/wait_sitl_disarm.py"
/usr/bin/python3 "$here/local_sitl_probe.py" command 300 "@$here/task_delivery_gps_7m.json" delivery_gps_7m
/usr/bin/python3 "$here/wait_sitl_disarm.py"
/usr/bin/python3 "$here/local_sitl_probe.py" command 300 "@$here/task_delivery_here.json" delivery_here
/usr/bin/python3 "$here/wait_sitl_disarm.py"
echo local_delivery_sequence_finished
