import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3'
rows=[json.loads(line) for line in (run/'onboard.jsonl').open()]
next_time=679.
for r in rows:
    if r.get('mission')!='RETURN_GATE_SEARCH' or r['stamp']<next_time:continue
    next_time=r['stamp']+10
    print(json.dumps({k:r.get(k) for k in ['stamp','pose','camera_state','banner_detail','avoidance','velocity_command']}))
print('keys',rows[-1].keys())
