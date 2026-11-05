"""Postflight evaluation joins independent geometry with recorded decisions.

No data from this analysis is supplied to any flight node.
"""
import bisect
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim'))
from check_track import lanes,to_lane,rect_gap

out=Path(sys.argv[1])
boards=[]
for line in (out/'onboard.jsonl').open():
    row=json.loads(line)
    if row.get('mission')=='RETURN_CORRIDOR': boards.append(row)
times=[r['stamp'] for r in boards]
layout=json.loads((out/'layout.json').read_text())
hx,hy=layout['home_world']
native=[]
for line in (out/'evaluation_vehicle_truth.jsonl').open():
    r=json.loads(line)
    if not(times[0]<=r['stamp']<=times[-1]):continue
    point=dict(x=r['x']-hx,y=r['y']-hy,z=r['z'])
    distances=[]
    for lane in lanes(layout):
        u,v=to_lane(point,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:
            distances.append(lane[4]/2-abs(v))
    for obstacle in layout.get('obstacles',[]):
        if r['z']<obstacle['h']+.3:
            distances.append(rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],point['x'],point['y']))
    native.append(dict(stamp=r['stamp'],xy=[point['x'],point['y']],clearance=min(distances)))
nt=[r['stamp'] for r in native]
commands=[]
for line in (out/'flight_commands.jsonl').open():
    r=json.loads(line);v=r['data']
    if r.get('topic')=='/mavros/setpoint_raw/local' and v.get('type_mask')==1479 and 878<=r['stamp']<=883:
        commands.append(r)
result=dict(first_native_violation=next((r for r in native if r['clearance']<.7),None),
            minimum_native=min(native,key=lambda r:r['clearance']),window=[])
for r in boards:
    if not(879<=r['stamp']<=883):continue
    d=r['avoidance'];i=bisect.bisect_left(nt,r['stamp']);truth=native[min(i,len(native)-1)]
    velocity=r['velocity'];sample=velocity['data']['header']['stamp']
    sample_t=sample['sec']+sample['nanosec']*1e-9
    result['window'].append(dict(stamp=r['stamp'],fcu_velocity_stamp=sample_t,
        velocity_age_s=r['stamp']-sample_t,xy=[r['pose']['data']['pose']['position'][k] for k in ('x','y')],
        native_clearance_m=truth['clearance'],lidar_clearance_m=d['observed_clearance_m'],
        fcu_velocity=[velocity['data']['twist']['linear'][k] for k in ('x','y')],
        disturbance=d['disturbance_world_mps'],disturbance_rate=d['disturbance_rate_world_mps2'],
        command=[d['cmd_vx'],d['cmd_vy_left']],hold=d.get('hold_source'),braking=d.get('braking_clearance_available')))
result['command_burst']=[dict(stamp=r['stamp'],xy=[r['data']['velocity'][k] for k in ('x','y')],yaw=r['data']['yaw_rate'])
    for r in commands if 879.5<=r['stamp']<=880.3]
print(json.dumps(result,indent=2))
