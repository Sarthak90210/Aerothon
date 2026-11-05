"""Freeze only observed barometer errors for evaluation, never mission input."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v35_targeted_20261008/my_world_random_s4'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];rows=[r for r in rows if r.get('pose')]
truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
start=min(rows,key=lambda r:abs(r['stamp']-662.32));epoch=start['stamp']
tt=np.array([float(n['t_sim']) for n in truth]);zz=np.array([float(n['z']) for n in truth]);errors=[]
for r in rows:
 if epoch-.2<=r['stamp']<=epoch+32:
  p=r['pose']['data'];s=p['header']['stamp'];t=s['sec']+s['nanosec']*1e-9
  errors.append([t,p['pose']['position']['z']-float(np.interp(t,tt,zz))])
fixture=dict(scope='Evaluation-only recorded barometer error replay with normal vertical actuator, horizontal flight unexercised',epoch=epoch,truth_alt=float(np.interp(epoch,tt,zz)),initial_vz=start['velocity']['data']['twist']['linear']['z'],hold_alt=2.64,errors=errors,original_source_archive='b97b74647bb4531e0b7f359d9653e726ab4276e7c0045bf19844c1dfd0aaa510',inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'evaluation_truth_track.csv']})
(root/'.scratch/simulation-reliability/altitude_v35_replay_fixture_20261008.json').write_text(json.dumps(fixture,indent=2))
print({k:fixture[k] for k in ['epoch','truth_alt','initial_vz','hold_alt']})
