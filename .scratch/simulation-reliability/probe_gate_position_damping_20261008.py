"""Vary only measured velocity damping; preserve the latched brake anchor."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'.scratch/simulation-reliability'))
from test_recorded_gate_physics_seam_20261008 import replay
results=[]
for gain in [.6,1.2,2.0]:
 result=replay(brake_gain=gain);result['brake_gain_s']=gain;results.append(result);print(json.dumps(result),flush=True)
(root/'logs/reliability_gate_position_damping_probe_20261008.json').write_text(json.dumps(results,indent=2))
