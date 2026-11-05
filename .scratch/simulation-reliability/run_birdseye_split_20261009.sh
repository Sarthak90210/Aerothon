#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
export GZ_PARTITION=aerothon_m2 GZ_IP=127.0.0.1
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER AEROTHON_MOTION_FORECAST_OUT
python3 - <<'PY'
import hashlib,json
from pathlib import Path
manifest=json.loads(Path('.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
PY
view="$PWD/.scratch/birdseye_split_v38_20261009_retry3"
mission="$PWD/logs/user_birdseye_split_v38_s20261003_retry3_20261009"
[[ ! -e "$view" && ! -e "$mission" ]] || { echo 'Recording output already exists'; exit 2; }
python3 -u .scratch/simulation-reliability/record_birdseye_split_20261009.py --out "$view" --mission "$mission" > "$PWD/logs/user_birdseye_camera_v38_retry3_20261009.log" 2>&1 & overhead=$!
status=0
bash .scratch/simulation-reliability/run_recorded_birdseye_acceptance_20261009.sh sim/worlds/split_corridors.json 20261003 "$mission" "$PWD/logs/delivery_profile_20261005.json" || status=$?
# The mission launcher closes the stack only after recording actual disarm.
for _ in $(seq 1 30); do kill -0 "$overhead" 2>/dev/null || break; sleep 1; done
kill -TERM "$overhead" 2>/dev/null || true
wait "$overhead" || true
printf '%s\n' "$status" > "$view/mission_evaluation_exit_code.txt"
echo 'User-requested mission recording closed; qualification remains paused.'
