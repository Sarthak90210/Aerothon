#!/usr/bin/env bash
set -euo pipefail
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_ENTRY=.scratch/simulation-reliability/return_entry_fresh_20261003.json
out=logs/reliability_render_return_receipt_model_20261006
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json 20261003 "$out" logs/delivery_profile_20261005.json || rc=$?
/usr/bin/python3 .scratch/simulation-reliability/grade_focused_return.py "$out"
