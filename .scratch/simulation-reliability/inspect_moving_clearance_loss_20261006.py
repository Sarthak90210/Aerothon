"""Postflight comparison of native clearance and recorded onboard decisions.

The operator driver's phases override the standby mission's WAITING label.
This analysis never publishes or supplies native geometry to drone software.
"""
import bisect
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim'))
from check_track import lanes,to_lane,rect_gap

out=Path(sys.argv[1])
driver=[json.loads(line) for line in (out/'trial_driver.jsonl').read_text().splitlines()]
times=[r['stamp'] for r in driver]
def active(t):
    i=bisect.bisect_right(times,t)-1
    return i>=0 and driver[i]['phase']=='RETURN_CORRIDOR'
boards=[json.loads(line) for line in (out/'onboard.jsonl').read_text().splitlines()]
boards=[r for r in boards if active(r['stamp']) and 'avoidance' in r and 'velocity' in r]
layout=json.loads((out/'layout.json').read_text());hx,hy=layout['home_world']
native=[]
for line in (out/'evaluation_vehicle_truth.jsonl').open():
    row=json.loads(line)
    if not active(row['stamp']):continue
    point=dict(x=row['x']-hx,y=row['y']-hy,z=row['z']);distances=[]
    for lane in lanes(layout):
        u,v=to_lane(point,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and row['z']<lane[5]:
            distances.append(lane[4]/2-abs(v))
    for obstacle in layout.get('obstacles',[]):
        if row['z']<obstacle['h']+.3:
            distances.append(rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],point['x'],point['y']))
    if distances:native.append(dict(stamp=row['stamp'],xy=[point['x'],point['y']],clearance=min(distances)))
first=next((r for r in native if r['clearance']<.7),None)
minimum=min(native,key=lambda r:r['clearance']) if native else None
centre=first['stamp'] if first else minimum['stamp'] if minimum else 0
def decision(row):
    d=row['avoidance'];velocity=row['velocity'];sample=velocity['data']['header']['stamp']
    captured=sample['sec']+sample['nanosec']*1e-9
    return dict(stamp=row['stamp'],xy=[row['pose']['data']['pose']['position'][k] for k in ('x','y')],
        fcu_capture_stamp=captured,fcu_receipt_stamp=velocity['received_stamp'],
        ground=[velocity['data']['twist']['linear'][k] for k in ('x','y')],
        state=d.get('state'),clearance=d.get('observed_clearance_m'),progress=d.get('axis_progress_m'),
        command=[d.get('cmd_vx'),d.get('cmd_vy_left')],wind=d.get('disturbance_world_mps'),
        rate=d.get('disturbance_rate_world_mps2'),estimate_valid=d.get('disturbance_estimate_valid'),
        planner=d.get('planner_state'),braking=d.get('braking_clearance_available'),hold=d.get('hold_source'))
report=dict(run=str(out),first_native_violation=first,minimum_native=minimum,
    handover=json.loads((out/'entry_handover.json').read_text()),
    initial_decisions=[decision(r) for r in boards if r['stamp']<=boards[0]['stamp']+2],
    failure_window=[decision(r) for r in boards if centre-3<=r['stamp']<=centre+2],
    evaluation_only=True)
print(json.dumps(report,indent=2))
