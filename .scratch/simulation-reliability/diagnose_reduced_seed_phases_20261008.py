import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for seed in (1,2,3):
 run=root/f'logs/reliability_reduced_seed_trials_20261008/my_world_field_s{seed}'
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text().splitlines()]
 phases=[]
 for r in rows:
  state=r.get('mission')
  if not phases or phases[-1]['state']!=state:phases.append(dict(state=state,start=r['stamp'],end=r['stamp']))
  phases[-1]['end']=r['stamp']
 for phase in phases:phase['duration']=round(phase['end']-phase['start'],2)
 fixture=json.loads((run/'run.json').read_text());grade=json.loads((run/'navigation_grade.json').read_text())
 result=dict(seed=seed,phases=phases,contacts=fixture['contacts'],clearance=grade['measured_corridor_clearance_m'])
 with (run/'phase_diagnosis_20261008.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
