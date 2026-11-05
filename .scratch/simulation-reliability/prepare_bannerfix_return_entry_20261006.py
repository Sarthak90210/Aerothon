"""Extract the failed full-run starting condition from recorded FCU data."""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root/'logs/reliability_render_my_world_s20261003_bannerfix_20261006/onboard.jsonl'
rows = [json.loads(line) for line in source.open()]
row = next(r for r in rows if r.get('mission') == 'RETURN_CORRIDOR')
approach = next(r for r in rows if r.get('mission') == 'GATE_CROSSING'
                and row['stamp'] - 30 < r['stamp'] < row['stamp'])
pose = row['pose']['data']['pose']
pos, q = pose['position'], pose['orientation']
ap = approach['pose']['data']['pose']['position']
dest = root/'.scratch/simulation-reliability/return_entry_bannerfix_20261003.json'
if dest.exists():
    raise SystemExit('Fixture already exists')
fixture = dict(x=pos['x'], y=pos['y'], alt=pos['z'],
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),
                   1-2*(q['y']**2+q['z']**2)),
    source=str(source.relative_to(root)),
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    captured_stamp=row['stamp'],
    purpose='focused operator starting condition from FCU pose; no geometry input to planner',
    approach=dict(x=ap['x'], y=ap['y'], captured_stamp=approach['stamp']),
    recorded_entry_velocity=row.get('velocity'))
dest.write_text(json.dumps(fixture, indent=2)+'\n')
print(json.dumps(fixture, indent=2))
