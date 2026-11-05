"""Retain distinct recorded views without claiming a full-rate camera ledger."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v23_targeted_20261008/my_world_random_s3'
seen=set();captures=[]
for line in (run/'onboard.jsonl').open():
    r=json.loads(line);d=r.get('banner_detail',{});stamp=d.get('capture_stamp');box=d.get('board_px')
    if r.get('mission')!='RETURN_GATE_SEARCH' or stamp in seen or stamp is None:continue
    seen.add(stamp)
    if not d.get('identified') or not box:continue
    captures.append(dict(stamp=r['stamp'],capture_stamp=stamp,box=box,bearing=d.get('bearing'),
        camera=r.get('camera_state'),pose=r.get('pose'),image_wh=d.get('image_wh')))
large=[r for r in captures if r['camera'].get('requested')=='FORWARD' and r['box'][1]<=1
    and r['box'][0]>1 and r['box'][0]+r['box'][2]<1279 and .48*720<=r['box'][3]<719]
review=dict(accepted_source=False,distinct_recorded_identified_views=captures,
    large_level_top_crops=large,evidence_limit='Snapshots and winch-arrival rows do not preserve every 20 Hz banner capture; no exact runtime streak is inferred',
    hypotheses=['Top-crop recovery rejects a genuine board extending over half the image',
                'Repeated side crops require a bounded range-independent framing backoff',
                'Blocked lidar orbit legs discard useful approach views'],
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'stack.log',run/'source_manifest.json']})
(run/'return_top_crop_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps(dict(distinct_identified=len(captures),large_level_top_crops=len(large),examples=large[:3]),indent=2))
