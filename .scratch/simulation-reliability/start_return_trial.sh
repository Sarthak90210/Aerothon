#!/usr/bin/env bash
set -euo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_ENTRY=sim/fixtures/return_entry_s20261003.json
out="${1:-logs/reliability_render_return_mount_retry1_20261006}"
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json 20261003 "$out" logs/delivery_profile_20261005.json || status=$?
# Full acceptance intentionally remains false for a focused trial.
/usr/bin/python3 .scratch/simulation-reliability/grade_focused_return.py "$out"
