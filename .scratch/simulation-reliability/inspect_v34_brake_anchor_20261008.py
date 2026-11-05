import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v34_targeted_20261008/my_world_random_s3'
for line in (run/'flight_commands.jsonl').open():
 r=json.loads(line);p=r.get('data',{}).get('pose',{}).get('position')
 if 803.5<r['stamp']<805.5 and p:print(r['stamp'],p)
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
for r in rows:
 if 803.5<r['stamp']<805.5 and r.get('pose'):print('pose',r['stamp'],r['pose']['data']['pose']['position'])
