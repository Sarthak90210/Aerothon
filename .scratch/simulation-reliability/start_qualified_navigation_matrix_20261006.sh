#!/usr/bin/env bash
# Prepared only. Launch manually after both current-source rendered seeds pass.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
first="${1:?current-source standard calm seed 20261003 output}"
second="${2:?current-source standard calm seed 1001 output}"
out="${3:?new campaign output directory}"
jobs="${4:-6}"
[[ "$jobs" =~ ^[0-9]+$ ]] && (( jobs >= 1 && jobs <= 16 )) || {
    echo 'Workers must be an integer from 1 to 16'; exit 2;
}
[[ ! -e "$out" ]] || { echo 'Output exists'; exit 2; }
# Do not compete with a rendered mission for sensor-processing resources.
if pgrep -f '[g]z sim|[a]rducopter|[l]aunch_level6_sim' >/dev/null; then
    echo 'Rendered stack active; navigation campaign was not started'; exit 2
fi
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1
python3 sim/run_navigation_campaign.py \
    --targeted "$first" "$second" --out "$out" -j "$jobs" --rtf 4
