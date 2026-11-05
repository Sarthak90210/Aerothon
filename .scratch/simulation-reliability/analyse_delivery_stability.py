"""Offline FCU evidence; never a simulator-to-drone signal."""
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

out=Path(sys.argv[1])
rows=[json.loads(line) for line in (out/'onboard.jsonl').open()]
states=[]
issues=defaultdict(int)
unloaded=[]
current=[]
longest=[]
threshold=.415636
for row in rows:
    if row.get('mission')!='WINCH_DROP' or not isinstance(row.get('observation'),dict):continue
    obs=row['observation']
    if not states or (obs['state'],obs['attempt'])!=(states[-1]['state'],states[-1]['attempt']):
        states.append(dict(stamp=obs['stamp'],state=obs['state'],attempt=obs['attempt'],reason=obs['reason']))
    if obs['state'] not in ('LOWER','TOUCHDOWN_WAIT'):continue
    try:
        t=row['stamp'];p=row['pose']['data'];q=p['pose']['orientation']
        velocity=row['velocity']['data']['twist']['linear']
        acceleration=row['imu']['data']['linear_acceleration']
        channels=row['motor_outputs']['data']['channels'][:4]
        effort=sum(((float(v)-1000)/1000)**2 for v in channels)/4
        ages={}
        for key in ('pose','velocity','imu','motor_outputs'):
            stamp=row[key]['data']['header']['stamp']
            ages[key]=t-stamp['sec']-stamp['nanosec']*1e-9
        roll=math.degrees(math.atan2(2*(q['w']*q['x']+q['y']*q['z']),1-2*(q['x']**2+q['y']**2)))
        pitch=math.degrees(math.asin(max(-1,min(1,2*(q['w']*q['y']-q['z']*q['x'])))))
        failures=[]
        if any(not 0<=age<=.5 for age in ages.values()):failures.append('stale telemetry')
        if abs(velocity['z'])>.15:failures.append('vertical velocity')
        if math.hypot(velocity['x'],velocity['y'])>.25:failures.append('horizontal velocity')
        if max(abs(roll),abs(pitch))>8:failures.append('attitude')
        if abs(math.sqrt(sum(acceleration[k]**2 for k in ('x','y','z')))-9.80665)>.6:failures.append('acceleration')
        if effort<threshold:
            unloaded.append(effort)
            for failure in failures:issues[failure]+=1
            if not failures:current.append(t)
            else:
                if len(current)>len(longest):longest=current
                current=[]
    except KeyError:pass
if len(current)>len(longest):longest=current
result=dict(transitions=states,unloaded_lowering_snapshots=len(unloaded),
    unloaded_effort_mean=statistics.mean(unloaded) if unloaded else None,
    disqualification_counts=dict(issues),longest_eligible_lowering_window_s=(longest[-1]-longest[0] if len(longest)>1 else 0),
    note='approximation from the passive FCU journal; controller callback timing may differ; no simulator truth used')
(out/'delivery_stability_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
