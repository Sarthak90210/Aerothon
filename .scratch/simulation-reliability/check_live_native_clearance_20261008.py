"""Operator-only live diagnostic; never an onboard decision input."""
import json,math,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from check_track import lanes,to_lane,rect_gap
out=Path(sys.argv[1]);layout=json.loads((out/'layout.json').read_text());home=layout.get('home_world',[0,0])
minimum=None;at=None;latest=None
with (out/'evaluation_vehicle_truth.jsonl').open() as f:
 for line in f:
  try:p=json.loads(line)
  except ValueError:continue
  latest=p
  if p['z']<=.3:continue
  r=dict(x=p['x']-home[0],y=p['y']-home[1],z=p['z'])
  gaps=[]
  for lane in lanes(layout):
   u,v=to_lane(r,layout,lane)
   if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:gaps.append(lane[4]/2-abs(v))
  for obstacle in layout.get('obstacles',[]):
   if r['z']<obstacle['h']+.3:
    gaps.append(rect_gap([(x-home[0],y-home[1]) for x,y in obstacle['poly']],r['x'],r['y']))
  if gaps and (minimum is None or min(gaps)<minimum):minimum=min(gaps);at=dict(stamp=p['stamp'],**r)
print(json.dumps(dict(scope='Live evaluation-only clearance, not final grade',minimum=minimum,at=at,latest=latest)))
