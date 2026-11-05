#!/usr/bin/env bash
set -e
repo='/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
cd "$repo"
export AEROTHON_OFFLINE_SCOPE_EVIDENCE='.scratch/slam_ui_20261018/offline_scope.json'
export AEROTHON_NATIVE_PYTHON="$repo/.scratch/pi_remote_runtime_20261014/testenv/bin/python"
# Windows Node runs the complete frontend suite/build separately.
bash scripts/run_tests.sh --reduced-scope --quick > .scratch/slam_ui_20261018/offline_checks.log 2>&1
