#!/usr/bin/env bash
set -euo pipefail
set +u
source /opt/ros/jazzy/setup.bash
set -u
export PATH=/usr/bin:/bin:$PATH PYTHONNOUSERSITE=1
out=logs/reliability_render_my_world_s20261003_bannerfix_20261006
[[ ! -e "$out/onboard.mp4" && ! -e "$out/video_timeline.json" ]]
ffmpeg -nostdin -v error -i "$out/onboard.avi" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$out/onboard.mp4"
ffmpeg -nostdin -v error -i "$out/onboard.mp4" -f null - 2> "$out/video_decode.log"
python3 sim/export_recording_timeline.py "$out" > "$out/video_export.log" 2>&1
grade_rc=0
python3 sim/evaluate_recorded_mission.py "$out" || grade_rc=$?
printf '%s\n' "$grade_rc" > "$out/manual_finalization_exit_code.txt"
exit "$grade_rc"
