#!/usr/bin/env bash
set -euo pipefail
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export AEROTHON_RENDER_TRIAL=delivery
out="${1:-logs/reliability_render_delivery_probe_20261006}"
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json 20261003 "$out" logs/delivery_profile_20261005.json || status=$?
# A focused trial never qualifies the full mission.
/usr/bin/python3 .scratch/simulation-reliability/grade_focused_delivery.py "$out"
