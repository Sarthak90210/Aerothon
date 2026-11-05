"""Offline delivery evidence only; no publishers or flight imports."""
import json
import math
import statistics
import sys
from pathlib import Path

out=Path(sys.argv[1])
trace=[json.loads(line) for line in (out/'onboard.jsonl').open()]
transitions=[]
for row in trace:
    obs=row.get('observation',{})
    if isinstance(obs,dict) and obs.get('state') and (
            not transitions or (obs['state'],obs.get('attempt')) !=
            (transitions[-1]['state'],transitions[-1].get('attempt'))):
        transitions.append(obs)
done=next((r for r in transitions if r['state']=='DONE'),None)
probe=next((r for r in transitions if r['state']=='PROBE'),None)
contacts=[json.loads(line) for line in (out/'evaluation_contacts.jsonl').open()]
ground=next((r['stamp'] for r in contacts if r.get('contacts')),None)
payload=[json.loads(line) for line in (out/'evaluation_truth.jsonl').open()]
window=[r for r in payload if probe and done and probe['stamp']<=r['stamp']<=done['stamp']]
result=dict(transitions=transitions,first_independent_contact_stamp=ground,
            source='offline native truth evaluation; never a drone decision input')
if window:
    initial=window[0]
    result['probe_through_confirmation']=dict(samples=len(window),
        min_height_m=min(r['z'] for r in window),max_height_m=max(r['z'] for r in window),
        max_displacement_m=max(math.dist((r['x'],r['y'],r['z']),
            (initial['x'],initial['y'],initial['z'])) for r in window))
profile=json.loads((out/'frozen_calibration.json').read_text())
result['frozen_profile']=profile
if done:
    final=next((r['stamp'] for r in reversed(transitions) if r['state']=='FINAL'),done['stamp'])
    effort=[]
    for row in trace:
        if not final<=row['stamp']<=done['stamp']:continue
        channels=row.get('motor_outputs',{}).get('data',{}).get('channels',[])
        if len(channels)<4:continue
        effort.append(sum(((float(v)-1000)/1000)**2 for v in channels[:4])/4)
    result['final_onboard_motor_effort']=dict(samples=len(effort),
        mean=statistics.mean(effort) if effort else None,
        minimum=min(effort,default=None),maximum=max(effort,default=None),
        basis='mean squared normalized FCU PWM, channels 0-3, PWM 1000-2000; not current')
(out/'delivery_interval_evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='transitions'},indent=2))
