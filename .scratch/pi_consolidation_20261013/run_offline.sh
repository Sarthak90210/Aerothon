#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PATH="$PWD/.scratch/pi_consolidation_20261013:/usr/bin:/bin:$PATH"
export PYTHONNOUSERSITE=1
export AEROTHON_OFFLINE_SCOPE_EVIDENCE="$PWD/logs/offline_pi_cleanup_scope_retry1_20261013.json"
bash scripts/run_tests.sh --reduced-scope > logs/offline_pi_cleanup_retry1_20261013.log 2>&1
result=$?
tail -25 logs/offline_pi_cleanup_retry1_20261013.log
exit "$result"
