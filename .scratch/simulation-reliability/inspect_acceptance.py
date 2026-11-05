"""Read-only live evidence snapshot. No drone subscriptions or publications."""
import bisect,json,math,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import navigation_grade
from recording_metrics import recording_metrics

out=Path(sys.argv[1])
def records(name):
    rows=[]
    for line in (out/name).open():
        try:rows.append(json.loads(line))
        except ValueError:pass  # a live write may not have finished
    return rows
onboard=records('onboard.jsonl')
last=onboard[-1]
result=dict(stamp=last['stamp'],mission=last.get('mission'),
    search_timing=last.get('search_timing'),avoidance=last.get('avoidance'))
if (out/'layout.json').exists():
    layout=json.loads((out/'layout.json').read_text())
    times=[r['stamp'] for r in onboard]
    track=[]
    for r in records('evaluation_vehicle_truth.jsonl'):
        i=bisect.bisect_right(times,r['stamp'])-1
        if i<0 or 'flight' not in onboard[i]:continue
        state=onboard[i]
        hx,hy=layout['home_world']
        qw,qx,qy,qz=r['quaternion']
        roll=math.degrees(math.atan2(2*(qw*qx+qy*qz),1-2*(qx*qx+qy*qy)))
        pitch=math.degrees(math.asin(max(-1,min(1,2*(qw*qy-qz*qx)))))
        track.append(dict(t=r['stamp'],x=r['x']-hx,y=r['y']-hy,z=r['z'],
            armed=state['flight']['data']['armed'],state=state.get('mission',''),
            mode=state['flight']['data']['mode'],roll=roll,pitch=pitch))
    # Only clearance statistics are used here; this is not acceptance grading.
    stats=navigation_grade(track,layout,None)
    result.update(red_clearance_m=stats['measured_red_clearance_m'],
        corridor_clearance_m=stats['measured_corridor_clearance_m'])
try:result['rates']=recording_metrics(out)
except ValueError:result['rates']='live row in progress'
print(json.dumps(result,indent=2))
