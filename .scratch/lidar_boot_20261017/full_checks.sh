#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source "$PWD/.scratch/lidar_boot_20261017/colcon_install/local_setup.bash"
export PATH="$PWD/.scratch/lidar_boot_20261017/bin:$PATH"
run_label=$(date -u +%Y%m%dT%H%M%SZ)
export AEROTHON_OFFLINE_SCOPE_EVIDENCE=".scratch/lidar_boot_20261017/offline_scope_${run_label}.json"
logfile=".scratch/lidar_boot_20261017/offline_${run_label}.log"
printf '%s\n' "$logfile" >.scratch/lidar_boot_20261017/latest_offline_log.txt
export AEROTHON_NATIVE_PYTHON="$PWD/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
bash scripts/run_tests.sh --reduced-scope >"$logfile" 2>&1
result=$?
tail -65 "$logfile"
exit "$result"
