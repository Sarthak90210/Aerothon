#!/usr/bin/env bash
# Isolated archived-source characterization. Never qualifies a future repair.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
snapshot="$root/.scratch/qualified_navigation_baseline_20261006"
out="$root/logs/reliability_navigation_baseline_matrix_20261006"
[[ ! -e "$out" ]] || { echo 'Campaign output already exists'; exit 2; }
if pgrep -f '[g]z sim|[a]rducopter|[l]aunch_level6_sim' >/dev/null; then
    echo 'Rendered stack active; matrix not started'; exit 2
fi
set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/aerothon_stack/install/setup.bash"
source "$root/install/setup.bash"
set -u
export PATH="/usr/bin:/bin:$PATH" PYTHONNOUSERSITE=1 ROS_LOCALHOST_ONLY=1
export PYTHONPATH="$snapshot/src/aerothon_mission/mission_bt:$snapshot/src/aerothon_avoidance/avoidance:$snapshot/src/aerothon_perception/camera_ctrl:$snapshot/src/aerothon_payload/winch_ctrl:$snapshot/src/aerothon_perception/perception_qr:$snapshot/src/aerothon_perception/perception_redzone:$snapshot/src/aerothon_perception/perception_banner:$snapshot/src/aerothon_sim/sim_gazebo:${PYTHONPATH:-}"
cd "$snapshot"
python3 - "$snapshot" <<'PY'
import hashlib,importlib,json,sys
from pathlib import Path
snapshot=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(snapshot/'sim'),str(snapshot/'scripts'),str(snapshot)]
modules=('mission_bt.mission_tree','avoidance.velocity_controller',
         'camera_ctrl.camera_ctrl_node','winch_ctrl.winch_node',
         'sim.navigation_mission','sim.headless_world',
         'perception_qr.qr_node','perception_redzone.redzone_node',
         'perception_banner.banner_node','world_spec','materialize_world',
         'test_corridor_stress','campaign_record','check_corridor_clearance')
evidence={}
for name in modules:
    module=importlib.import_module(name)
    path=Path(module.__file__).resolve()
    assert path.is_relative_to(snapshot), 'Decision import escaped snapshot: '+name
    evidence[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(snapshot/'decision_import_verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('Decision imports originate from verified snapshot',flush=True)
PY
python3 sim/run_navigation_campaign.py \
    --targeted "$root/logs/reliability_render_my_world_s20261003_handover_guard_20261006" \
               "$root/logs/reliability_render_my_world_s1001_handover_guard_20261006" \
    --out "$out" -j 6 --rtf 4
