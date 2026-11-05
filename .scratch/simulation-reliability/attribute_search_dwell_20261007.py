"""Attribute search dwell using saved FCU velocity/pose captures only."""
import json,math,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=Path(sys.argv[1]);run=run if run.is_absolute() else root/run
rows=[json.loads(l) for l in (run/'onboard.jsonl').open()]
stats={};previous=None
for row in rows:
 state=row.get('mission')
 if previous is not None and state==previous.get('mission'):
  dt=row['stamp']-previous['stamp']
  velocity=(row.get('velocity') or {}).get('data',{}).get('twist',{}).get('linear',{})
  if 0<dt<1 and all(k in velocity for k in ('x','y')):
   speed=math.hypot(velocity['x'],velocity['y'])
   item=stats.setdefault(state,dict(captured_interval_s=0.,low_speed_below_0_1_s=0.,slow_below_0_3_s=0.,velocity_distance_m=0.,samples=0))
   item['captured_interval_s']+=dt;item['velocity_distance_m']+=speed*dt;item['samples']+=1
   if speed<.1:item['low_speed_below_0_1_s']+=dt
   if speed<.3:item['slow_below_0_3_s']+=dt
 previous=row
interesting={name:item for name,item in stats.items() if name in ('SEARCH_QR','RETURN_GATE_SEARCH','BANNER_ALIGN','RETURN_TRANSIT','GATE_CROSSING','RETURN_CORRIDOR')}
for item in interesting.values():item['low_speed_fraction']=item['low_speed_below_0_1_s']/item['captured_interval_s'];item['mean_captured_speed_mps']=item['velocity_distance_m']/item['captured_interval_s']
result=dict(scope='Saved FCU sample attribution; low speed is not automatically a fault or a braking event',phases=interesting,not_a_final_grade=True)
with (run/'fcU_phase_velocity_attribution_20261007.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
