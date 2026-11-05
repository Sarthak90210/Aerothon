#!/usr/bin/env bash
set -euo pipefail
export AEROTHON_RENDER_TRIAL=return-corridor
export AEROTHON_CORRIDOR_HANDOVER=moving
export AEROTHON_CORRIDOR_ENTRY=.scratch/simulation-reliability/return_entry_bannerfix_20261003.json
out=logs/reliability_render_return_handover_guard_moving_20261006
runner_rc=0
bash scripts/run_recorded_acceptance.sh sim/worlds/my_world.json 20261003 "$out" logs/delivery_profile_20261005.json || runner_rc=$?
printf '%s\n' "$runner_rc" > "$out/recording_runner_exit_code.txt"
focused_rc=0
/usr/bin/python3 .scratch/simulation-reliability/grade_focused_return.py "$out" || focused_rc=$?
/usr/bin/python3 .scratch/simulation-reliability/archive_recorded_source.py "$out"
exit "$focused_rc"
