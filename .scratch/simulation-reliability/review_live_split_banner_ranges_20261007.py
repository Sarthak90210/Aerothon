"""Post-capture range audit; world geometry is evaluation-only and never sent to nodes."""
import bisect,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_render_split_corridors_s20261003_banner_capture_continuity_20261007'
layout=json.loads((run/'layout.json').read_text());hx,hy=layout['home_world']
rx,ry=layout['corridors']['return'][:2];truth=(rx-hx,ry-hy)
rows=[]
for line in (run/'onboard.jsonl').open():
    try:rows.append(json.loads(line))
    except json.JSONDecodeError:continue
poses=[]
for row in rows:
    message=row.get('pose',{}).get('data',{})
    if not message:continue
    stamp=message['header']['stamp'];capture=stamp['sec']+stamp['nanosec']*1e-9
    position=message['pose']['position'];q=message['pose']['orientation']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    poses.append((capture,position['x'],position['y'],position['z'],yaw))
poses=sorted(set(poses));times=[p[0] for p in poses]
focal=640/math.tan(.851919/2)
return_start=min((row['stamp'] for row in rows if row.get('mission')=='RETURN_GATE_SEARCH'),default=math.inf)
seen=[]
for row in rows:
    if row.get('mission') not in ('RETURN_GATE_SEARCH','BANNER_ALIGN'):continue
    if row['stamp']<return_start:continue
    detail=row.get('banner_detail',{})
    if not detail.get('identified'):continue
    box=detail.get('board_px');iw,ih=(detail.get('image_wh') or [1280,720])[:2]
    if not box or box[0]<=1 or box[1]<=1 or box[0]+box[2]>=iw-1 or box[1]+box[3]>=ih-1:continue
    area=detail.get('board_area_px',0);capture=detail.get('capture_stamp')
    if not area or capture is None:continue
    i=max(0,bisect.bisect_right(times,capture)-1);pose=poses[i]
    if capture-pose[0]>.2:continue
    bearing=detail.get('bearing',0);angle=pose[4]+math.atan(bearing*math.tan(.851919/2))
    distance=focal*math.sqrt(3.7*1.15/area)
    estimated=(pose[1]+distance*math.cos(angle),pose[2]+distance*math.sin(angle))
    seen.append(dict(stamp=row['stamp'],capture=capture,stage=row['mission'],pose=pose,
        board_px=detail.get('board_px'),area_px=area,estimated_face_on_range_m=distance,
        estimated_board_xy=estimated,evaluation_return_gate_range_m=math.dist(pose[1:3],truth),
        evaluation_point_error_m=math.dist(estimated,truth),detail=detail))
selected=[]
for stage in ('RETURN_GATE_SEARCH','BANNER_ALIGN'):
    matching=[r for r in seen if r['stage']==stage]
    if matching:selected.extend([matching[0],matching[-1]])
report=dict(scope='Live recording diagnostic; simulator coordinates used only for independent evaluation',
    recording_complete=False,pose_match='preceding recorded FCU pose within 0.20 s, not decision-side pairing',
    identified_samples=len(seen),selected=selected,causality_established=False,production_changed=False,
    excludes_outbound_alignment=True,excludes_edge_clipped_boards=True,
    earlier_review_scope='Raw classifications also included clipped/outbound frames; not decision-eligible sightings')
target=root/'logs/reliability_live_split_banner_range_eligible_review_20261007.json'
with target.open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps(dict(identified_samples=len(seen),selected=[{k:r[k] for k in
    ('stamp','capture','stage','board_px','estimated_face_on_range_m','evaluation_return_gate_range_m','evaluation_point_error_m')}
    for r in selected]),indent=2))
