"""Read only recent complete rows; no live observation is qualification."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];version=sys.argv[1]
parent=root/f'logs/reliability_reduced_{version}_targeted_20261008'
for run in sorted(parent.glob('my_world_*')):
    p=run/'onboard.jsonl'
    if not p.exists():continue
    with p.open('rb') as f:
        f.seek(max(0,p.stat().st_size-250000));lines=f.read().splitlines()
    last=None
    for line in reversed(lines):
        try:row=json.loads(line)
        except (ValueError,UnicodeError):continue
        if 'flight' in row:last=row;break
    if last is None:continue
    a=last.get('avoidance') or {};flight=last['flight']['data']
    print(json.dumps(dict(run=run.name,t=last['stamp'],phase=last.get('mission'),armed=flight.get('armed'),connected=flight.get('connected'),mode=flight.get('mode'),fault=a.get('fault'),vertical_fault=a.get('altitude_motion_fault'),qualified=False)))
if (parent/'report.json').exists():
    r=json.loads((parent/'report.json').read_text())
    print(json.dumps(dict(batch_closed=True,executed=r['executed_cases'],pass_navigation=r['pass_navigation'])))
