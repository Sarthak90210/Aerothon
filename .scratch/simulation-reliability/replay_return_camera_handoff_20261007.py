"""Postflight projection replay; fixture geometry stays outside decision code."""
import ast,csv,json,math,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_sim/sim_gazebo')]
import headless_world as H
out=root/'logs/reliability_monotonic_search_escape_field_s2_navigation_20261007/my_world_field_s2'
arena=H.Arena(H.W.load(out/'world_spec.json'),'d')
rows=[json.loads(l) for l in (out/'onboard.jsonl').open()]
align=next(r['stamp'] for r in rows if r.get('mission')=='BANNER_ALIGN' and r['stamp']>600)
truth=list(csv.DictReader((out/'evaluation_truth_track.csv').open()))
records=[]
hfov_values=[]
for node in ast.walk(ast.parse((root/'sim/fly_headless.py').read_text())):
    if isinstance(node,ast.Dict):
        for key,value in zip(node.keys,node.values):
            if isinstance(key,ast.Constant) and key.value=='camera_hfov':
                hfov_values.append(ast.literal_eval(value))
assert len(hfov_values)==1
hfov=float(hfov_values[0])
for r in rows:
    if not align<=r['stamp']<=align+2:continue
    native=min(truth,key=lambda t:abs(float(t['t_sim'])-r['stamp']))
    q=r['pose']['data']['pose']['orientation']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    p=np.array([float(native[k]) for k in ('x','y','z')])
    eye=p+np.array([.16*math.cos(yaw),.16*math.sin(yaw),0.])
    model=SimpleNamespace(arena=arena,camera=H.Camera(hfov),yaw=yaw)
    b=next(b for b in arena.banners if b['name']=='return')
    project=lambda pitch:H.HeadlessWorld._board_view(model,b['xy'],b['facing'],H.BOARD_W,b['z0'],b['z1'],eye,pitch)
    coarse=[];fine=[]
    for degrees in range(0,360,15):
        model.yaw=yaw+math.radians(degrees)
        view=project(math.radians(20))
        framed=bool(view and view[4]>=.7 and view[2]<=H.BANNER_MAX_INCIDENCE and view[5]<=15)
        item=dict(offset_deg=degrees,admissible_geometry=framed,view=view)
        fine.append(item)
        if degrees%45==0:coarse.append(item)
    model.yaw=yaw
    records.append(dict(stamp=r['stamp'],camera=r['camera_state'],truth_xyz=p.tolist(),
                        forward=project(0.),banner=project(math.radians(20)),
                        coarse_headings=coarse,fine_headings=fine))
result=dict(scope='Postflight camera projection replay only; no live controller fixture input',camera_hfov=hfov,
            prior_60_degree_projection_invalid_for_runtime=True,records=records)
with (out/'return_camera_handoff_runtime_hfov_projection_20261007.json').open('x') as f:json.dump(result,f,indent=2)
print('samples',len(records),'forward visible',sum(r['forward'] is not None for r in records),'banner visible',sum(r['banner'] is not None for r in records))
print('runtime HFOV',hfov,'first pose coarse geometry admissible',sum(x['admissible_geometry'] for x in records[0]['coarse_headings']),
      'fine geometry admissible',sum(x['admissible_geometry'] for x in records[0]['fine_headings']))
