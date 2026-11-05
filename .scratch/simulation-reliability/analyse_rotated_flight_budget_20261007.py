"""Analyze a closed recording's flight budget without changing flight decisions."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_render_rb_rotated_s20261003_observation_repairs_20261007'
assert (out/'recorded_result.json').exists(), 'Wait for actual completed mission'
rows=[]
for line in (out/'onboard.jsonl').read_text().splitlines():
    item=json.loads(line)
    if 'mission' in item:
        rows.append(item)
stages=[]
for row in rows:
    if not stages or stages[-1]['state']!=row['mission']:
        stages.append(dict(state=row['mission'],first_observed_sim_s=row['stamp']))
for before,after in zip(stages,stages[1:]):
    before['observed_duration_sim_s']=after['first_observed_sim_s']-before['first_observed_sim_s']
result=json.loads((out/'recorded_result.json').read_text())
armed=[row for row in rows if row.get('flight',{}).get('data',{}).get('armed')]
summary=dict(scope='Independent closed recording timing; never flight input',
    mission_result=result,stages=stages,
    armed_observation_span_s=armed[-1]['stamp']-armed[0]['stamp'],
    onboard_source_sha256=hashlib.sha256((out/'onboard.jsonl').read_bytes()).hexdigest(),
    requirement_s=900.,acceptance_override=False)
target=out/'flight_budget_review_20261007.json'
with target.open('x') as handle:json.dump(summary,handle,indent=2)
print(json.dumps(summary,indent=2))
