#!/usr/bin/env bash
# Phase 2: the clarified arena, rendered. Dimensions reach the aircraft only
# through the GCS (AEROTHON_GCS_PRESET, applied by scripts/gcs_operator.py
# before START); the mission is launched without the arena's QR size.
set -o pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
# Temporary: a real drone is on 14550/14551 via Mission Planner.
export AEROTHON_SITL_PORT_SHIFT=100
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER
status=0
for tag in h115_suspended; do
  out="$PWD/logs/phase2_rendered_clarified_${tag}_s20261003_p2r8"
  echo "=== $tag ==="
  export AEROTHON_GCS_PRESET="Aerothon 2026 sim ${tag}"
  export AEROTHON_GCS_PRESET_FILE="$PWD/sim/arena_presets/aerothon26_${tag}.json"
  bash scripts/run_recorded_acceptance.sh "sim/worlds/clarified_${tag}.json" 20261003 "$out" \
       "$PWD/logs/delivery_profile_20261005.json" || status=$?
  python3 - "$out" "$tag" <<'PY'
import json,sys
from pathlib import Path
out,tag=Path(sys.argv[1]),sys.argv[2]
s=json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else {}
g=json.loads((out/'grade.json').read_text()) if (out/'grade.json').exists() else {}
d=json.loads((out/'gcs_dimensions.json').read_text()) if (out/'gcs_dimensions.json').exists() else {}
print(json.dumps(dict(world=tag,acceptance_pass=s.get('acceptance_pass'),failures=s.get('failures'),
  flight_time_s=s.get('flight_time_s'),gcs_applied=d.get('ok')),indent=1))
PY
  # Domain-wide stop between runs: a survivor contaminated r4-r6.
  bash /mnt/c/Users/sarth/AppData/Local/Temp/claude/D--MY-DOCUMENTS-VIT-Team-Rotor-Fpv-AEROTHON/35c169e9-61b9-4faf-8b4d-3b206c8097c7/scratchpad/stop_mission_stack.sh >/dev/null 2>&1 || true
done
exit "$status"
