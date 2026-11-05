#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER AEROTHON_MOTION_FORECAST_OUT
python3 - <<'PY'
import json
from pathlib import Path
r=Path('logs/reliability_reduced_seed_trials_20261008/report.json')
assert json.loads(r.read_text())['pass_navigation'], 'Reduced seeds must pass before rendered acceptance'
assert Path('logs/reliability_reduced_scope_source_20261008/installed_startup_imports.json').exists()
PY
for trial in my_world:20261003 my_world:1001 shipped:20261003 rb_rotated:20261003 split_corridors:20261003; do
 world="${trial%:*}"; seed="${trial#*:}"
 python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items()), 'Final frozen source changed'
PY
 out="$PWD/logs/reliability_reduced_render_${world}_s${seed}_20261008"
 bash scripts/run_recorded_acceptance.sh "sim/worlds/$world.json" "$seed" "$out" "$PWD/logs/delivery_profile_20261005.json"
done
