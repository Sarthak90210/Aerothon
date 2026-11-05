"""Change only camera tilt at the recorded position and recorded yaw."""
import csv,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_sim/sim_gazebo')]
import headless_world as H
run=root/'logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3';arena=H.Arena(H.W.load(run/'world_spec.json'),'c')
truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()));rows=[json.loads(l) for l in (run/'onboard.jsonl').open()]
b=next(b for b in arena.banners if b['name']=='return');records=[]
for t in [741,752,765]:
 r=min((r for r in rows if r.get('pose') and r.get('mission')=='RETURN_GATE_SEARCH'),key=lambda r:abs(r['stamp']-t));n=min(truth,key=lambda n:abs(float(n['t_sim'])-r['stamp']));p=np.array([float(n[k]) for k in ['x','y','z']]);q=r['pose']['data']['pose']['orientation'];yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2));model=SimpleNamespace(arena=arena,camera=H.Camera(.851919),yaw=yaw);eye=p+np.array([.16*math.cos(yaw),.16*math.sin(yaw),0.]);probes=[]
 for name,pitch in [('BANNER',math.radians(20)),('FORWARD',0.)]:
  v=H.HeadlessWorld._board_view(model,b['xy'],b['facing'],H.BOARD_W,b['z0'],b['z1'],eye,pitch)
  probes.append(dict(camera=name,view=v,identifiable=bool(v and v[3]>=H.BANNER_MIN_BOARD_PX and v[2]<=H.BANNER_MAX_INCIDENCE and v[4]>=.7 and v[5]<=15)))
 records.append(dict(stamp=r['stamp'],actual_xyz=p.tolist(),recorded_yaw=yaw,recorded_camera=r['camera_state'],probes=probes))
report=dict(qualified=False,limitation='Snapshot yaw, nearest .1 s truth position; geometry replay only, not stochastic detector or runtime callback reconstruction',records=records,inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'evaluation_truth_track.csv',run/'world_spec.json']})
(run/'orbit_tilt_projection_diagnosis.json').write_text(json.dumps(report,indent=2));print(json.dumps(records,indent=2))
