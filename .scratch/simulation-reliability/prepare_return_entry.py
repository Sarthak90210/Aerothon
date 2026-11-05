"""Create a focused starting fixture from FCU data, never simulator truth."""
import hashlib
import json
import math
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'logs/reliability_render_my_world_s20261003_retry2_20261005/onboard.jsonl'
rows=[json.loads(line) for line in source.open()]
row=next(r for r in rows if r.get('mission')=='RETURN_CORRIDOR')
approach=next(r for r in rows if r.get('mission')=='GATE_CROSSING' and row['stamp']-30<r['stamp']<row['stamp'])
pose=row['pose']['data']['pose'];p,q=pose['position'],pose['orientation']
entry=dict(x=p['x'],y=p['y'],alt=p['z'],yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)),
    source=str(source.relative_to(root)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    captured_stamp=row['stamp'],purpose='operator starting condition for focused rendered return test; not course knowledge for planner')
position=approach['pose']['data']['pose']['position']
entry['approach']=dict(x=position['x'],y=position['y'],captured_stamp=approach['stamp'],
    reason='descend outside the gate, then approach horizontally under the board; recorded FCU pose')
directory=root/'sim/fixtures';directory.mkdir(exist_ok=True)
path=directory/'return_entry_s20261003.json';path.write_text(json.dumps(entry,indent=2)+'\n')
print(json.dumps(entry,indent=2))
