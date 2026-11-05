#!/usr/bin/env bash
set -e
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source install/setup.bash
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_DOMAIN_ID=219
bash -n scripts/run_recorded_acceptance.sh
python3 -m py_compile sim/campaign_record.py sim/run_navigation_campaign.py sim/fly_headless.py sim/evaluate_recorded_mission.py
python3 -m pytest -q sim/test_recording_metrics.py sim/test_corridor_clearance_contract.py
python3 - <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,'scripts')
from check_corridor_clearance import audit
results=[audit(p,lane_key=k) for p in sorted(Path('sim/worlds').glob('*.json')) for k in ('corridor','return_corridor')]
Path('logs/reliability_fixture_geometry.json').write_text(json.dumps(results,indent=2))
for r in results:print(Path(r['world']).name,r['lane'],r['classification'],r['grid_bottlenecks_m'])
PY
