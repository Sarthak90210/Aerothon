"""Archive recorded identification/stand-off geometry; no mission inputs change."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v33_targeted_20261008/my_world_field_s3'
rows=[];previous=None;phases=[];seen=set();sample=None
for line in (run/'onboard.jsonl').open():
    row=json.loads(line)
    phase=row.get('mission')
    if phase!=previous:
        phases.append((row['stamp'],phase));previous=phase
    detail=row.get('banner_detail',{})
    if sample is None and 570<row['stamp']<585:
        sample={k:row.get(k) for k in ('stamp','banner_detail','observation','camera_state')}
    if isinstance(detail,dict) and isinstance(detail.get('data'),str):
        detail=json.loads(detail['data'])
    if row['stamp']>560 and detail.get('identified'):
        key=detail.get('capture_stamp')
        if key not in seen:
            seen.add(key)
            rows.append(dict(stamp=row['stamp'],phase=phase,banner=detail,
                             camera=row.get('camera_state'),pose=row.get('pose'),
                             observation=row.get('observation')))
out=dict(qualified=False,phases=phases,identified=rows)
(run/'return_banner_handoff_diagnosis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(phases=phases,identified_count=len(rows),first=rows[:1],last=rows[-1:],sample=sample),indent=2))
