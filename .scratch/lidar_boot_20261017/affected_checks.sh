#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
bash .scratch/lidar_boot_20261017/checks.sh \
  tests/test_web_robustness.py tests/test_boot_connection.py \
  sim/test_lidar_pipeline_quality.py sim/test_lidar_calibration_gcs.py \
  sim/test_lidar_registration.py sim/test_lidar_odometry.py \
  sim/test_mav_router_broadcast.py sim/test_launch_defaults.py sim/test_real_path_wiring.py \
  -q -rs --tb=short > .scratch/lidar_boot_20261017/affected_final.log 2>&1
result=$?
cat .scratch/lidar_boot_20261017/affected_final.log
exit "$result"
