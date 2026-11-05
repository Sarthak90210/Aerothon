"""Resolve live startup decision modules against the exact reduced freeze."""
import hashlib,importlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
manifest=json.loads((root/'.scratch/reduced_scope_v24_candidate_20261008/source_manifest.json').read_text())
modules={'mission_bt.mission_tree':'src/aerothon_mission/mission_bt/mission_bt/mission_tree.py',
 'mission_bt.gate_braking':'src/aerothon_mission/mission_bt/mission_bt/gate_braking.py',
 'mission_bt.search_braking':'src/aerothon_mission/mission_bt/mission_bt/search_braking.py',
 'avoidance.velocity_controller':'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py',
 'perception_banner.banner_node':'src/aerothon_perception/perception_banner/perception_banner/banner_node.py',
 'perception_qr.qr_node':'src/aerothon_perception/perception_qr/perception_qr/qr_node.py'}
modules.update({'mission_bt.mav_commander':'src/aerothon_mission/mission_bt/mission_bt/mav_commander.py','avoidance.local_planner':'src/aerothon_avoidance/avoidance/avoidance/local_planner.py','camera_ctrl.camera_ctrl_node':'src/aerothon_perception/camera_ctrl/camera_ctrl/camera_ctrl_node.py'})
modules["mission_bt.banner_captures"]="src/aerothon_mission/mission_bt/mission_bt/banner_captures.py"
modules["mission_bt.leg_router"]="src/aerothon_mission/mission_bt/mission_bt/leg_router.py"
records={}
for name,path in modules.items():
 actual=Path(importlib.import_module(name).__file__).resolve();assert actual==(root/path).resolve(),str(actual)
 sha=hashlib.sha256(actual.read_bytes()).hexdigest();assert sha==manifest[path],name
 records[name]=dict(file=str(actual),sha256=sha)
out=root/'logs/reliability_reduced_scope_v24_source_20261008/installed_startup_imports.json'
with out.open('x') as f:json.dump(records,f,indent=2)
print(json.dumps(records,indent=2))
