"""Distinguish crossing intent and latched braking around the failed minimum."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v34_targeted_20261008/my_world_random_s3'
review=json.loads((run/'corridor_clearance_diagnosis.json').read_text());r=review['minimum']['onboard']
print(json.dumps({k:r.get(k) for k in ('stamp','pose','velocity','observation')},indent=2))
previous=None
for line in (run/'flight_commands.jsonl').open():
    row=json.loads(line)
    if not 790<row['stamp']<825:continue
    p=row.get('data',{}).get('pose',{}).get('position')
    if p!=previous:
        print(json.dumps(dict(stamp=row['stamp'],topic=row.get('topic'),position=p)))
        previous=p
