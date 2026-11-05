"""Archive observed return views; do not infer a complete raw camera history."""
import hashlib,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v17_normal_timing_retry_20261008/my_world_random_s3'
path=run/'onboard.jsonl';seen=set();captures=[];phase={}
for line in path.read_text().splitlines():
    row=json.loads(line);detail=row.get('banner_detail',{});stamp=detail.get('capture_stamp')
    if row.get('mission')=='BANNER_ALIGN' and row['stamp']>800:
        phase.setdefault('first_recorded_stamp',row['stamp']);phase['last_recorded_stamp']=row['stamp']
    if stamp is None or stamp in seen:continue
    seen.add(stamp)
    box=detail.get('board_px');wh=detail.get('image_wh') or [1280,720]
    if (row.get('mission')!='BANNER_ALIGN' or row['stamp']<800
            or not detail.get('identified') or box is None
            or not (box[0]<=1 or box[0]+box[2]>=wh[0]-1)):continue
    pose=row.get('pose',{}).get('data',{}).get('pose',{});q=pose.get('orientation',{})
    yaw=math.atan2(2*(q.get('w',0)*q.get('z',0)+q.get('x',0)*q.get('y',0)),
                   1-2*(q.get('y',0)**2+q.get('z',0)**2)) if q else None
    captures.append(dict(recorded_stamp=row['stamp'],capture_stamp=stamp,
        processed_stamp=detail.get('processed_stamp'),board_px=box,image_wh=wh,
        bearing=detail.get('bearing'),text_confirmed=detail.get('text_confirmed'),
        recorded_camera_state=row.get('camera_state'),recorded_pose=pose,
        recorded_pose_yaw=yaw,pose_basis='snapshot measurement, not reconstructed capture-time pose'))
review=dict(hypotheses=[
    'Fresh horizontal clips during yaw settlement are ignored by dwell-only framing',
    'Camera tilt rather than horizontal framing causes missing views',
    'Incorrect board identity or replayed capture aliases cause apparent sightings',
    'Accepted range or square-up geometry is wrong'],
    observed_alignment_interval=phase,distinct_identified_horizontal_clips=captures,
    diagnosed_seam='AlignToBanner._settle only invokes top-height recovery; horizontal framing was dwell-only',
    evidence_limit='Passive onboard snapshots plus winch-arrival rows are not the full 20 Hz raw camera history; no exact four-frame runtime streak is claimed from these snapshots',
    actual_leaf_red='logs/reliability_v19_turning_width_crop_red_20261008.log',
    actual_leaf_focused_green='logs/reliability_v19_return_focused_20261008.log',
    candidate='V19: four distinct fresh identified clipped captures, capture-associated bearing; existing 2 m distance and shared maximum of two backoffs',
    thresholds_unchanged=True,accepted_source=False,
    files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
           for p in [path,run/'stack.log',run/'source_manifest.json',run/'configuration.json']})
(run/'return_width_framing_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps(dict(distinct_identified_horizontal_clips=len(captures),interval=phase,qualification=False)))
