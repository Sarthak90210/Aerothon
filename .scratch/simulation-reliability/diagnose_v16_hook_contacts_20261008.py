"""Explain each rejected native hook contact without altering its grade."""
import bisect
import json
import math
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008'
def read(name):
    rows=[]
    for line in (out/name).read_text().splitlines():
        try: rows.append(json.loads(line))
        except ValueError: pass
    return rows
onboard=read('onboard.jsonl');poses=read('evaluation_vehicle_truth.jsonl')
ts=[r['stamp'] for r in onboard];pt=[r['stamp'] for r in poses]
layout=json.loads((out/'layout.json').read_text());target=json.loads((out/'evaluation_target.json').read_text())['target'];pad=layout['pads'][target]
accepted=0;rejected=[]
for row in read('evaluation_vehicle_contacts.jsonl'):
    if row.get('kind')!='contacts' or row['link'] not in ('claw_jaw_a','claw_jaw_b'):continue
    stamp=row['stamp'];i=bisect.bisect_left(pt,stamp);choices=[j for j in (i-1,i) if 0<=j<len(poses)]
    pose=poses[min(choices,key=lambda j:abs(pt[j]-stamp))] if choices else {}
    j=bisect.bisect_right(ts,stamp)-1;state=onboard[j] if j>=0 else {}
    winch=state.get('winch_capture',{});data=winch.get('data',{});receipt=winch.get('received_stamp',float('-inf'))
    for pair in row['contacts']:
        if 'delivery_zone_40x30::field::collision' not in (pair['collision1'],pair['collision2']):continue
        positions=pair.get('positions',[])
        checks=dict(mission=state.get('mission')=='WINCH_DROP',body_height=pose.get('z',0)>=2.,pose_fresh=abs(pose.get('stamp',float('-inf'))-stamp)<=.3,
            snapshot_fresh=0<=stamp-state.get('stamp',float('-inf'))<=.3,
            winch_fresh=math.isfinite(receipt) and 0<=stamp-receipt<=.3,
            winch_state=data.get('state') in ('LOWERING','IDLE','STOWING','RELEASING'),winch_fault=not data.get('fault'),payout=data.get('payout_estimate_m',0)>=1.,
            actual_positions=bool(positions),target_floor=bool(positions) and all(abs(p['z'])<=.2 and math.hypot(p['x']-pad[0],p['y']-pad[1])<=1. for p in positions))
        if all(checks.values()):accepted+=1
        else:
            next_state=onboard[j+1] if j+1<len(onboard) else {}
            rejected.append(dict(stamp=stamp,link=row['link'],failed=[k for k,v in checks.items() if not v],snapshot=state.get('stamp'),winch_received=receipt,winch_age=stamp-receipt,
                next_snapshot=next_state.get('stamp'),next_winch_received=next_state.get('winch_capture',{}).get('received_stamp'),winch=data,
                body_pose=pose,positions=positions,max_target_distance=max((math.hypot(p['x']-pad[0],p['y']-pad[1]) for p in positions),default=None)))
result=dict(hypotheses=['5 Hz snapshot aliases fresh winch arrivals','capture timestamps use mismatched clocks','actual hook positions exceed target tolerance','body pose or mission phase is stale','winch state/fault/payout is unsafe'],thresholds_unchanged=True,accepted_pairs=accepted,rejected_pairs=len(rejected),failure_counts=dict(Counter(k for r in rejected for k in r['failed'])),rejected=rejected)
(out/'hook_contact_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='rejected'}))
for row in rejected[:3]:print(json.dumps(row))
