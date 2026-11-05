"""Extract an operator starting condition from FCU pose only."""
import hashlib,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=root/'logs/reliability_render_my_world_s20261003_gustfix_20261006/onboard.jsonl'
rows=[json.loads(v) for v in source.open()]
r=next(v for v in rows if v.get('mission')=='RETURN_CORRIDOR')
approach=next(v for v in rows if v.get('mission')=='GATE_CROSSING' and r['stamp']-30<v['stamp']<r['stamp'])
p=r['pose']['data']['pose'];q=p['orientation'];pos=p['position'];ap=approach['pose']['data']['pose']['position']
dest=root/'.scratch/simulation-reliability/return_entry_fresh_20261003.json';assert not dest.exists()
dest.write_text(json.dumps(dict(x=pos['x'],y=pos['y'],alt=pos['z'],yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)),source=str(source.relative_to(root)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),captured_stamp=r['stamp'],purpose='focused starting condition from FCU pose, no geometry input to planner',approach=dict(x=ap['x'],y=ap['y'],captured_stamp=approach['stamp'])),indent=2)+'\n')
print(dest)
