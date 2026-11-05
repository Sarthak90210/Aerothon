#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER AEROTHON_MOTION_FORECAST_OUT
python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "$PWD/logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008" "$PWD/logs/delivery_profile_20261005.json"
