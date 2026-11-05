"""Locate the unchanged clearance check's minimum in independent records."""
import bisect,csv,hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'scripts')]
from check_track import lanes,to_lane,rect_gap
run=root/'logs/reliability_reduced_v34_targeted_20261008/my_world_random_s3'
layout=json.loads((run/'layout.json').read_text());hx,hy=layout['home_world']
onboard=[json.loads(s) for s in (run/'onboard.jsonl').open()];onboard=[r for r in onboard if 'flight' in r]
times=[r['stamp'] for r in onboard];minimum=None;near=[]
for raw in csv.DictReader((run/'evaluation_truth_track.csv').open()):
    if raw['armed']!='1' or float(raw['z'])<=.3:continue
    row=dict(t=float(raw['t_sim']),x=float(raw['x']),y=float(raw['y']),z=float(raw['z']))
    candidates=[]
    for i,lane in enumerate(lanes(layout)):
        u,v=to_lane(row,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and row['z']<lane[5]:candidates.append((lane[4]/2-abs(v),f'lane {i}',u,v))
    for i,obstacle in enumerate(layout.get('obstacles',[])):
        if row['z']<obstacle['h']+.3:candidates.append((rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],row['x'],row['y']),f'obstacle {i}',None,None))
    if not candidates:continue
    gap,kind,u,v=min(candidates)
    if minimum is None or gap<minimum['gap']:
        index=bisect.bisect_right(times,row['t'])-1
        minimum=dict(gap=gap,kind=kind,truth=row,lane_u=u,lane_v=v,onboard=onboard[index] if index>=0 else None)
    if gap<.71:near.append(dict(gap=gap,kind=kind,truth=row))
lidar=[json.loads(s) for s in (run/'onboard_lidar.jsonl').open()]
nearest=sorted(lidar,key=lambda r:abs(r['received_stamp']-minimum['truth']['t']))[:3]
review=dict(accepted_source=False,minimum=minimum,near_threshold_truth=near,nearby_recorded_lidar=nearest,
    limitation='Recorder/controller subscriptions are independent; arrival order must be checked in a controller replay',
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'evaluation_truth_track.csv',run/'onboard.jsonl',run/'onboard_lidar.jsonl',run/'navigation_grade.json']})
(run/'corridor_clearance_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps(dict(gap=minimum['gap'],kind=minimum['kind'],truth=minimum['truth'],phase=minimum['onboard'].get('mission'),
    avoidance=minimum['onboard'].get('avoidance'),near_threshold_samples=len(near)),indent=2))
