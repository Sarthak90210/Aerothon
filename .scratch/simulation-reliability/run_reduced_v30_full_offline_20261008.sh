#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PATH="/home/sarthak/.nvm/versions/node/v24.18.0/bin:/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export ROS_DOMAIN_ID=20 ROS_LOCALHOST_ONLY=1
python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_v30_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
bash scripts/run_tests.sh 2>&1 | tee logs/reliability_reduced_v30_full_offline_20261008.log
python3 .scratch/simulation-reliability/close_reduced_v30_offline_20261008.py
