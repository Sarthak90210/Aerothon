#!/usr/bin/env bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PATH=/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH
export AEROTHON_OFFLINE_SCOPE_EVIDENCE="$PWD/.scratch/gcs_merge_20261014/quiet-offline-scope.json"
bash scripts/run_tests.sh --reduced-scope > .scratch/gcs_merge_20261014/quiet-full.log 2>&1
rc=$?
tail -45 .scratch/gcs_merge_20261014/quiet-full.log
exit "$rc"
