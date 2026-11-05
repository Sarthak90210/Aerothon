"""Freeze only the failing gate's observed error stream as a test fixture."""
import csv,hashlib,json,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v28_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
start=min((r for r in rows if r.get('pose')),key=lambda r:abs(r['stamp']-749.));n=min(truth,key=lambda n:abs(float(n['t_sim'])-start['stamp']));p=start['pose']['data']['pose'];q=p['orientation'];v=start['velocity']['data']['twist']['linear']
tt=np.array([float(n['t_sim']) for n in truth]);tx=np.array([[float(n[k]) for k in ['x','y','z']] for n in truth]);errors=[]
for r in rows:
 if start['stamp']-.2<=r['stamp']<=start['stamp']+61 and r.get('pose'):
  xyz=r['pose']['data']['pose']['position'];true=np.array([np.interp(r['stamp'],tt,tx[:,k]) for k in range(3)])
  errors.append([r['stamp'],*[xyz[k]-true[i] for i,k in enumerate(['x','y','z'])]])
fixture=dict(scope='Evaluation fixture for actual gate leaf, lidar guard and normal-response physics; never a mission input',epoch=start['stamp'],position=[float(n[k]) for k in ['x','y','z']],yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)),ground_velocity=[v[k] for k in ['x','y','z']],conditions=json.loads((run/'run.json').read_text())['conditions'],errors=errors,target=[14.89813394656775,-15.884451067649756],flight_alt=2.7701346731707823,flight_distance=6.509,original_source_archive='20ac779c2748d870980b75fd95f7b159ad2341f05d0abe8d3d1442b8ec7188ef',inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'evaluation_truth_track.csv',run/'run.json']})
(root/'sim/fixtures/gate_entry_mild_s3_20261008.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
print('Frozen evaluation-only gate fixture',len(errors),'observed error samples')
