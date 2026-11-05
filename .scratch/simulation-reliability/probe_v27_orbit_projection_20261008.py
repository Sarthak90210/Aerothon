"""Actual captured geometry is evaluation data only, never navigation input."""
import csv,json,math,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_sim/sim_gazebo')]
import headless_world as H
run=root/'logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3'
arena=H.Arena(H.W.load(run/'world_spec.json'),'c');truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()));rows=[json.loads(l) for l in (run/'onboard.jsonl').open()];out=[]
for t in [717,729,741,752,765]:
 r=min((r for r in rows if r.get('pose') and r.get('mission')=='RETURN_GATE_SEARCH'),key=lambda r:abs(r['stamp']-t));native=min(truth,key=lambda n:abs(float(n['t_sim'])-r['stamp']));p=np.array([float(native[k]) for k in ['x','y','z']]);q=r['pose']['data']['pose']['orientation'];yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2));model=SimpleNamespace(arena=arena,camera=H.Camera(.851919),yaw=yaw)
 b=next(b for b in arena.banners if b['name']=='return');eye=p+np.array([.16*math.cos(yaw),.16*math.sin(yaw),0.]);probes=[]
 for raise_m in [0,2]:
  look_eye=eye+np.array([0,0,raise_m]);theta=math.atan2(b['xy'][1]-eye[1],b['xy'][0]-eye[0]);model.yaw=theta
  v=H.HeadlessWorld._board_view(model,b['xy'],b['facing'],H.BOARD_W,b['z0'],b['z1'],look_eye,0.)
  probes.append(dict(raise_m=raise_m,view=v,identifiable=bool(v and v[3]>=H.BANNER_MIN_BOARD_PX and v[2]<=H.BANNER_MAX_INCIDENCE and v[4]>=.7 and v[5]<=15)))
 out.append(dict(stamp=r['stamp'],measured_z=r['pose']['data']['pose']['position']['z'],actual_xyz=p.tolist(),probes=probes))
(run/'orbit_camera_projection_diagnosis.json').write_text(json.dumps(dict(accepted=False,limitation='Geometry replay with yaw toward board; diagnostic only; no stochastic detector, controller or runtime callback reconstruction',records=out),indent=2));print(json.dumps(out,indent=2))
