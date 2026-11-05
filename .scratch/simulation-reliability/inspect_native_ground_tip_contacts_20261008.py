import json
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'logs/reliability_reduced_v3_render_split_corridors_s20261003_20261008'
grade=json.loads((out/'grade.json').read_text());e=grade['aircraft_contact_evidence'];unexpected=e['unexpected_contacts']
rows=[json.loads(s) for s in (out/'onboard.jsonl').read_text().splitlines()]
result=dict(valid=e['valid'],unexpected_count=len(unexpected),pairs=dict(Counter((r['vehicle']+' -> '+r['other']) for r in unexpected)),time_range=[min(r['stamp'] for r in unexpected),max(r['stamp'] for r in unexpected)],samples=[])
for t in (274.212,280.,285.49):
 r=min(rows,key=lambda r:abs(r['stamp']-t))
 result['samples'].append({k:r.get(k) for k in ('stamp','mission','winch','pose')})
layout=json.loads((out/'layout.json').read_text());result['layout_keys']=list(layout);result['pads']=layout.get('pads');result['targets']=layout.get('targets')
(out/'ground_tip_contact_diagnosis_20261008.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
