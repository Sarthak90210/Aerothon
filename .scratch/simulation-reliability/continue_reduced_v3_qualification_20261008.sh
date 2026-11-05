#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd '/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON'
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1
while :; do
 if [[ -f logs/reliability_reduced_v3_render_split_corridors_s20261003_20261008/summary.json ]]; then
  python3 - <<'PY'
import json
from pathlib import Path
assert json.loads(Path('logs/reliability_reduced_v3_render_split_corridors_s20261003_20261008/summary.json').read_text())['acceptance_pass'], 'Split acceptance failed; no further qualification dispatched'
PY
  [[ ! -f logs/reliability_reduced_scope_v3_source_20261008/full_offline_closed_review.json ]] || break
 fi
 if grep -q 'OFFLINE CHECKS FAILED' logs/reliability_reduced_v3_full_offline_20261008.log; then echo 'Offline suite failed; continuation stopped'; exit 1; fi
 sleep 20
done
bash .scratch/simulation-reliability/run_reduced_v3_remaining_rendered_20261008.sh
python3 sim/run_navigation_campaign.py --reduced-no-strong-or-delay -j 6 --rtf 4 --out logs/reliability_reduced_v3_campaign_20261008 --targeted \
 logs/reliability_reduced_v3_render_my_world_s20261003_20261008 \
 logs/reliability_reduced_v3_render_my_world_s1001_20261008 \
 logs/reliability_reduced_v3_render_shipped_s20261003_20261008 \
 logs/reliability_reduced_v3_render_rb_rotated_s20261003_20261008 \
 logs/reliability_reduced_v3_render_split_corridors_s20261003_20261008
