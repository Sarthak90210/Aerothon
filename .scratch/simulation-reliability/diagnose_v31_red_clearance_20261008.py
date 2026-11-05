"""Locate the independent red-clearance failure; no mission input changes."""
import bisect,csv,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v31_targeted_20261008/my_world_random_s3'
layout=json.loads((run/'layout.json').read_text());home=layout['home_world']
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];rows=[r for r in rows if r.get('pose')];times=[r['stamp'] for r in rows]
minimum=None;near=[]
for raw in csv.DictReader((run/'evaluation_truth_track.csv').open()):
 if raw['armed']!='1' or float(raw['z'])<=.3:continue
 xyz=[float(raw[k]) for k in ('x','y','z')];t=float(raw['t_sim'])
 for name,(x,y,width,height,yaw) in layout['red_zones'].items():
  dx,dy=xyz[0]+home[0]-x,xyz[1]+home[1]-y;c,s=math.cos(yaw),math.sin(yaw)
  u,v=c*dx+s*dy,-s*dx+c*dy
  gap=math.hypot(max(abs(u)-width/2,0),max(abs(v)-height/2,0))
  if minimum is None or gap<minimum['clearance_m']:
   i=max(0,bisect.bisect_right(times,t)-1);r=rows[i]
   minimum=dict(clearance_m=gap,zone=name,t=t,truth_local=xyz,onboard=r)
  if gap<1.5:near.append(dict(t=t,gap=gap,zone=name))
t=minimum['t'];events=[]
for line in (run/'flight_commands.jsonl').open():
 r=json.loads(line)
 if t-3<=r['stamp']<=t+3:events.append(r)
output=dict(minimum=minimum,below_required=near,commands=events,qualified=False)
(run/'red_clearance_diagnosis.json').write_text(json.dumps(output,indent=2))
r=minimum['onboard'];print(json.dumps(dict(clearance_m=minimum['clearance_m'],zone=minimum['zone'],stamp=t,truth=minimum['truth_local'],phase=r.get('mission'),pose=r['pose']['data']['pose'],exclusion_count=len(r.get('red_timing',{}).get('exclusions',[])),red_status=r.get('red_timing',{}).get('status'),near_samples=len(near),commands=[dict(stamp=e['stamp'],topic=e['topic'],position=e['data'].get('pose',{}).get('position')) for e in events[::5]]),indent=2))
