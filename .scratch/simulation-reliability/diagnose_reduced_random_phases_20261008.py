import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for seed in (3,4):
 run=root/f'logs/reliability_reduced_v3_random_targeted_20261008/my_world_random_s{seed}'
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text().splitlines()];phases=[]
 for r in rows:
  state=r.get('mission')
  if not phases or phases[-1]['state']!=state:phases.append(dict(state=state,start=r['stamp'],end=r['stamp']))
  phases[-1]['end']=r['stamp']
 fixture=json.loads((run/'run.json').read_text());result=dict(seed=seed,phases=phases,conditions=fixture['conditions'],contacts=fixture['contacts'])
 with (run/'phase_diagnosis_20261008.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(seed=seed,phases=[(p['state'],round(p['end']-p['start'],1)) for p in phases],conditions=fixture['conditions'])))
