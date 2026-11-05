#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source .scratch/pi_remote_runtime_20261014/testenv/bin/activate
export PATH=/home/sarthak/.nvm/versions/node/v24.18.0/bin:$PATH
attempt=${1:?new evidence attempt ID required}
export AEROTHON_OFFLINE_SCOPE_EVIDENCE="$PWD/.scratch/pi_remote_runtime_20261014/offline-scope-$attempt.json"
output=".scratch/pi_remote_runtime_20261014/offline-$attempt.log"
test ! -e "$output" || exit 1
bash scripts/run_tests.sh --reduced-scope >"$output" 2>&1
rc=$?
tail -n 35 "$output"
exit "$rc"
