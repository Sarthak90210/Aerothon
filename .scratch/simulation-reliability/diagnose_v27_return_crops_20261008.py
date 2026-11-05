"""Passive snapshots, not a full-rate leaf or banner callback ledger."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3'
seen=set();records=[]
for line in (run/'onboard.jsonl').open():
    r=json.loads(line);d=r.get('banner_detail') or {};t=d.get('capture_stamp');b=d.get('board_px')
    if r.get('mission')!='RETURN_GATE_SEARCH' or t in seen or not d.get('identified') or not b:continue
    seen.add(t);wh=d.get('image_wh') or [1280,720]
    records.append(dict(clock=r['stamp'],capture=t,box=b,bearing=d.get('bearing'),camera=r.get('camera_state'),pose=r.get('pose'),side=b[0]<=1 or b[0]+b[2]>=wh[0]-1,top=b[1]<=1,bottom=b[1]+b[3]>=wh[1]-1))
review=dict(accepted_source=False,distinct_views=records,limitation='Passive snapshots cannot establish every leaf callback or every 20 Hz capture',files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'navigation_grade.json']})
(run/'return_crop_sequence_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps([dict(t=r['capture'],side=r['side'],top=r['top'],bottom=r['bottom'],camera=r['camera'].get('requested'),box=r['box'],bearing=r['bearing']) for r in records[:50]],indent=2))
