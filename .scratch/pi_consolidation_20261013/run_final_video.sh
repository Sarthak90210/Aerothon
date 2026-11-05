#!/usr/bin/env bash
set -o pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
export AEROTHON_ACCEPTANCE_DOMAIN=30 ROS_DOMAIN_ID=30 ROS_LOCALHOST_ONLY=1
export AEROTHON_SITL_PORT_SHIFT=100 AEROTHON_RENDER_CONDITIONS=field
export AEROTHON_RECORD_OVERVIEW=1
export AEROTHON_GCS_PRESET='Aerothon 2026 sim h115_both'
export AEROTHON_GCS_PRESET_FILE="$PWD/sim/arena_presets/aerothon26_h115_both.json"
unset AEROTHON_RENDER_TRIAL AEROTHON_CORRIDOR_ENTRY AEROTHON_CORRIDOR_HANDOVER
out="$PWD/logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013"
bash scripts/run_recorded_acceptance.sh sim/worlds/clarified_h115_both.json \
  20261004 "$out" "$PWD/logs/delivery_profile_20261005.json" \
  > logs/pi_cleanup_hard_field_runner_retry1_20261013.log 2>&1
result=$?
printf 'Acceptance exit: %s\n' "$result"
if [[ -f "$out/summary.json" ]]; then
 python3 sim/export_overview.py "$out"
fi
exit "$result"
