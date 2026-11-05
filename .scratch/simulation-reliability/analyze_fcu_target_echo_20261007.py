"""Postflight association of own packets with FCU target telemetry.
Echo timestamps bound first observation of a target, not exact receipt time.
"""
import bisect,json,math,statistics,sys
from pathlib import Path
out=Path(sys.argv[1]);rows=[json.loads(l) for l in (out/'fcu_target_echo_observations.jsonl').open()]
def stamp(r):
    t=r['data']['header']['stamp'];return t['sec']+t['nanosec']*1e-9
poses=[];commands=[];echoes=[]
for r in rows:
    d=r['data'];t=stamp(r)
    if t<=0:continue
    if r['topic'].endswith('/pose'):
        q=d['pose']['orientation'];yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
        if not poses or t>poses[-1][0]:poses.append((t,yaw))
    elif r['topic']=='/mavros/setpoint_raw/local' and d.get('type_mask')==1479:
        commands.append((t,[d['velocity']['x'],d['velocity']['y']]))
    elif r['topic']=='/mavros/setpoint_raw/target_local' and not d.get('type_mask',0)&24:
        echoes.append((t,[d['velocity']['x'],d['velocity']['y']],d['coordinate_frame']))
commands.sort();echoes.sort();ct=[r[0] for r in commands];pt=[r[0] for r in poses]
def heading(t):
    i=bisect.bisect_right(pt,t)
    if i==0:return poses[0][1]
    if i==len(poses):return poses[-1][1]
    a,b=poses[i-1],poses[i];f=(t-a[0])/(b[0]-a[0]);return a[1]+f*math.atan2(math.sin(b[1]-a[1]),math.cos(b[1]-a[1]))
matched=[];ambiguous=0;unmatched=0;previous=None;used=set()
for t,vel,frame in echoes:
    if frame!=1 or math.hypot(*vel)<.08:continue
    co,si=math.cos(heading(t)),math.sin(heading(t));matches=[]
    for sent,body in commands[bisect.bisect_left(ct,t-.8):bisect.bisect_right(ct,t+.005)]:
        world=[co*body[0]-si*body[1],si*body[0]+co*body[1]]
        error=math.dist(world,vel)
        if error<=.015:matches.append((sent,error))
    if len(matches)==1:
        sent,error=matches[0]
        if sent not in used:
            matched.append(dict(issued_stamp=sent,first_matching_echo_stamp=t,
                observed_echo_lag_upper_s=t-sent,vector_error_mps=error,echo_velocity_world=vel))
            used.add(sent)
    elif matches:ambiguous+=1
    else:unmatched+=1
lags=sorted(r['observed_echo_lag_upper_s'] for r in matched if r['observed_echo_lag_upper_s']>=0)
report=dict(scope='Own issued velocity and FCU target echoes; no simulator truth or parameter changes',
    raw_velocity_echoes=len(echoes),unique_first_matches=len(matched),ambiguous_echoes=ambiguous,unmatched_echoes=unmatched,
    median_first_echo_lag_upper_s=statistics.median(lags) if lags else None,
    p95_first_echo_lag_upper_s=lags[min(len(lags)-1,math.ceil(.95*len(lags))-1)] if lags else None,
    matches=matched,qualified_transport_bound=False,
    limitations=['Echo header is FCU send time, not the instant a packet arrived.',
        'Approximate yaw association uses captured onboard poses; ambiguous signatures are excluded.',
        'Echo bandwidth and packet dropout require qualification before changing the controller model.'])
with (out/'fcu_target_echo_timing_review_20261007.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='matches'},indent=2))
