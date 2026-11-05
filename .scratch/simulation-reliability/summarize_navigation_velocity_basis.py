"""Read-only accounting of the velocity source used in recorded navigation."""
import bisect,collections,json,sys
from pathlib import Path
out=Path(sys.argv[1]);driver=[]
if (out/'trial_driver.jsonl').exists():
    for line in (out/'trial_driver.jsonl').open():
        try:driver.append(json.loads(line))
        except ValueError:pass
times=[v['stamp'] for v in driver];basis=collections.Counter();faults=collections.Counter();ages=[];count=0
for line in (out/'onboard.jsonl').open():
    try:r=json.loads(line)
    except ValueError:continue
    phase=r.get('mission')
    if driver:
        i=bisect.bisect_right(times,r['stamp'])-1
        if i>=0:phase=driver[i]['phase']
    if phase not in ('CORRIDOR_NAV','RETURN_CORRIDOR'):continue
    d=r.get('avoidance') or {}
    if d.get('state')=='OBSERVING':continue
    count+=1;basis[str(d.get('ground_velocity_basis','not recorded'))]+=1
    if d.get('fault'):faults[d['fault']]+=1
    if isinstance(d.get('fcu_velocity_age_s'),(int,float)):ages.append(d['fcu_velocity_age_s'])
print(json.dumps(dict(navigation_samples=count,basis=dict(basis),faults=dict(faults),maximum_recorded_velocity_age_s=max(ages) if ages else None,source='recorded onboard decisions and driver phases only; no simulator truth'),indent=2))
