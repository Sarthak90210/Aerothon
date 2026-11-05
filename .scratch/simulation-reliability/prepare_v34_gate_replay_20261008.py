"""Evaluation-only replay from independently recorded truth and FCU errors."""
import csv,hashlib,json,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v34_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
start=min((r for r in rows if r.get('pose')),key=lambda r:abs(r['stamp']-792.31))
tt=np.array([float(n['t_sim']) for n in truth]);tx=np.array([[float(n[k]) for k in ['x','y','z']] for n in truth])
epoch=start['stamp'];p=start['pose']['data']['pose'];q=p['orientation'];v=start['velocity']['data']['twist']['linear']
errors=[]
for r in rows:
 if epoch-.2<=r['stamp']<=epoch+61 and r.get('pose'):
  data=r['pose']['data'];s=data['header']['stamp'];stamp=s['sec']+s['nanosec']*1e-9
  xyz=data['pose']['position'];true=[np.interp(stamp,tt,tx[:,k]) for k in range(3)]
  errors.append([stamp,*[xyz[k]-true[i] for i,k in enumerate(['x','y','z'])]])
fixture=dict(scope='Evaluation only; recorded errors interpolated, ROS callback timing and wind RNG not fully reconstructed',epoch=epoch,position=[float(np.interp(epoch,tt,tx[:,k])) for k in range(3)],yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)),ground_velocity=[v[k] for k in ['x','y','z']],conditions=json.loads((run/'run.json').read_text())['conditions'],errors=errors,target=[15.661798470232908,-15.301094242874083],flight_alt=2.7045235718774183,flight_distance=6.2,inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'evaluation_truth_track.csv',run/'run.json']})
dest=root/'.scratch/simulation-reliability/gate_v34_replay_fixture_20261008.json';dest.write_text(json.dumps(fixture,indent=2))
source=(root/'sim/test_gate_motion_physics.py').read_text().replace("ROOT=Path(__file__).resolve().parents[1]","ROOT=Path(__file__).resolve().parents[2]").replace("ROOT/'sim/fixtures/gate_entry_mild_s3_20261008.json'","ROOT/'.scratch/simulation-reliability/gate_v34_replay_fixture_20261008.json'")
source=source.replace("minimum=float('inf');status", "trace=[];minimum=float('inf');status")
source=source.replace('status=leaf.update();next_tick',"status=leaf.update();trace.append(dict(t=w.t,phase=leaf._phase,p=w.p.tolist(),est=est.tolist(),speed=mav.delivery_inputs.get('speed'),hold=leaf._brake_hold,progress=leaf._cross_displacement.copy()));next_tick")
source=source.replace("print(dict(status", "(ROOT/'.scratch/simulation-reliability/gate_v34_replay_trace_20261008.json').write_text(json.dumps(trace,indent=2))\n    print(dict(status")
(root/'.scratch/simulation-reliability/test_v34_gate_physics_seam_20261008.py').write_text(source)
print(dict(epoch=epoch,position=fixture['position'],yaw=fixture['yaw'],error_samples=len(errors)))
