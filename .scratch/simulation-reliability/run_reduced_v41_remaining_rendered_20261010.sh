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
import json
from pathlib import Path
source=Path('logs/reliability_reduced_scope_v41_source_20261010')
assert json.loads((source/'targeted_closed_review.json').read_text())['pass_navigation']
assert json.loads((source/'full_offline_closed_review.json').read_text())['all_offline_checks_pass']
assert json.loads(Path('logs/reliability_reduced_v41_render_split_corridors_s20261003_20261010/summary.json').read_text())['acceptance_pass']
PY
for trial in my_world:20261003 my_world:1001 shipped:20261003 rb_rotated:20261003; do
 world="${trial%:*}"; seed="${trial#*:}"
 python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_v41_candidate_20261010/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
 out="$PWD/logs/reliability_reduced_v41_render_${world}_s${seed}_20261010"
 bash scripts/run_recorded_acceptance.sh "sim/worlds/$world.json" "$seed" "$out" "$PWD/logs/delivery_profile_20261005.json"
done
