#!/usr/bin/env bash
# The three banner placements the organisers allow, flown as full rendered
# missions: a banner on the ground only, a suspended banner only, and both.
# Each run owns the stack in turn; the native stage uses ROS domain 30.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER
status=0
for world in banner_suspended banner_ground banner_both; do
  out="$PWD/logs/banner_rendered_${world}_s20261003_20261011"
  echo "=== $world ==="
  bash scripts/run_recorded_acceptance.sh "sim/worlds/$world.json" 20261003 "$out" \
       "$PWD/logs/delivery_profile_20261005.json" || status=$?
  python3 - "$out" "$world" <<'PY'
import json,sys
from pathlib import Path
out,world=Path(sys.argv[1]),sys.argv[2]
summary=json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else {}
grade=json.loads((out/'grade.json').read_text()) if (out/'grade.json').exists() else {}
checks=grade.get('checks',{})
print(json.dumps(dict(world=world,acceptance_pass=summary.get('acceptance_pass'),
  checks_passed=sum(1 for v in checks.values() if v),checks_total=len(checks),
  failures=summary.get('failures'),
  corridor_clearance_m=grade.get('measured_corridor_clearance_m'),
  flight_time_s=summary.get('flight_time_s'),
  final_armed=summary.get('final_armed')),indent=1))
PY
done
exit "$status"
