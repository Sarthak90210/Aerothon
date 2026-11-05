import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'.scratch/simulation-reliability'))
from test_recorded_gate_physics_seam_20261008 import replay
result=replay(motion_arrival=True)
(root/'logs/reliability_gate_motion_arrival_probe_20261008.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert result['status']=='Status.SUCCESS'
assert not result['contacts'] and result['minimum_clearance_m']>=.70
