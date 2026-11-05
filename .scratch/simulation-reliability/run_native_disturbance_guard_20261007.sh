#!/usr/bin/env bash
set -euo pipefail
cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/native_disturbance_guard_candidate_20261007"
set +u
source install/setup.bash
set -u
export ROS_DOMAIN_ID=218 ROS_LOCALHOST_ONLY=1 PYTHONNOUSERSITE=1
python3 - <<'PY'
import hashlib,inspect
from avoidance import velocity_controller
p=inspect.getfile(velocity_controller)
assert '/native_disturbance_guard_candidate_20261007/' in p,p
assert hashlib.sha256(open(p,'rb').read()).hexdigest()=='ee144216f8fc59fd9b9d444166491003516183155fff6d011c0c0f4caab5a30f'
print(p)
PY
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_ENTRY="/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/simulation-reliability/split_return_entry_20261007.json"
export AEROTHON_CORRIDOR_HANDOVER=stationary
unset AEROTHON_MOTION_FORECAST_OUT
bash scripts/run_recorded_acceptance.sh sim/worlds/split_corridors.json 20261003 "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/logs/reliability_render_split_return_disturbance_guard_20261007" "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/logs/delivery_profile_20261005.json"
