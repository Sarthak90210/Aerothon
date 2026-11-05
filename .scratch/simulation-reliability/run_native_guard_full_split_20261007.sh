#!/usr/bin/env bash
set -euo pipefail
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/native_disturbance_guard_candidate_20261007"
set +u
source install/setup.bash
set -u
export ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1 PYTHONNOUSERSITE=1
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER AEROTHON_MOTION_FORECAST_OUT
python3 - <<'PY'
import hashlib,inspect
from avoidance import velocity_controller
p=inspect.getfile(velocity_controller)
assert '/native_disturbance_guard_candidate_20261007/' in p,p
assert hashlib.sha256(open(p,'rb').read()).hexdigest()=='ee144216f8fc59fd9b9d444166491003516183155fff6d011c0c0f4caab5a30f'
print(p)
PY
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/logs/reliability_render_split_guard_full_s20261003_20261007" "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/logs/delivery_profile_20261005.json"
