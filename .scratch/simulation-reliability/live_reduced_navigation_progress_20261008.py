"""Passive phase timing only; live data never qualifies a mission."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];version=sys.argv[1]
for run in sorted((root/f'logs/reliability_reduced_{version}_targeted_20261008').glob('my_world_*')):
    if not (run/'onboard.jsonl').exists():
        continue
    phase=[];previous=None;last=None
    for line in (run/'onboard.jsonl').open():
        try:r=json.loads(line)
        except ValueError:continue
        if r.get('mission') and r['mission']!=previous:
            phase.append([r['stamp'],r['mission']]);previous=r['mission']
        if 'flight' in r:last=r
    if last is None:continue
    start=next((t for t,p in phase if p=='RETURN_TRANSIT'),None)
    end=next((t for t,p in phase if p=='CAMERA_BANNER' and start is not None and t>start),None)
    print(json.dumps(dict(run=run.name,stamp=last['stamp'],phase=last.get('mission'),flight=last['flight']['data'],
        high_return_duration_s=end-start if start is not None and end is not None else None,
        recent_phases=phase[-10:],qualified=False)))
