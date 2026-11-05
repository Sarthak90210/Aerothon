"""Attribute independent native clearance violations to recorded stages."""
import bisect
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim'))
from check_track import lanes,to_lane,rect_gap
out=Path(sys.argv[1])
def read(name):
    result=[]
    for line in (out/name).open():
        try:result.append(json.loads(line))
        except ValueError:pass
    return result
onboard=read('onboard.jsonl')
times=[r['stamp'] for r in onboard]
layout=json.loads((out/'layout.json').read_text())
hx,hy=layout.get('home_world',[0,0])
violations=[]
minimum={}
for truth in read('evaluation_vehicle_truth.jsonl'):
    i=bisect.bisect_right(times,truth['stamp'])-1
    if i<0:continue
    board=onboard[i]
    if not board.get('flight',{}).get('data',{}).get('armed') or truth['z']<=.3:continue
    r=dict(t=truth['stamp'],x=truth['x']-hx,y=truth['y']-hy,z=truth['z'])
    candidates=[]
    for index,lane in enumerate(lanes(layout)):
        u,v=to_lane(r,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:
            candidates.append((lane[4]/2-abs(v),f'lane {index} wall'))
    for index,obstacle in enumerate(layout.get('obstacles',[])):
        if r['z']<obstacle['h']+.3:
            candidates.append((rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],r['x'],r['y']),f'obstacle {index}'))
    if not candidates:continue
    clearance,surface=min(candidates)
    stage=board.get('mission','')
    event=dict(**r,stage=stage,clearance=clearance,surface=surface,
        avoidance=board.get('avoidance'))
    if stage not in minimum or clearance<minimum[stage]['clearance']:minimum[stage]=event
    if clearance<.7:violations.append(event)
result=dict(per_stage_minimum=minimum,violating_native_samples=len(violations),
    first_violation=violations[0] if violations else None,
    minimum_violation=min(violations,key=lambda r:r['clearance']) if violations else None,
    source='independent native simulator truth for evaluation only')
(out/'clearance_failure_attribution.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
