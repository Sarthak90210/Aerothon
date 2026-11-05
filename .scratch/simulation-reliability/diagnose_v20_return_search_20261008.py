"""Replay recorded green regions; snapshot evidence is not a 20 Hz ledger."""
import hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.banner_orbit import green_fix
run=root/'logs/reliability_reduced_v20_targeted_20261008/my_world_random_s3'
rows=[json.loads(line) for line in (run/'onboard.jsonl').open()]
seen=set();captures=[];changes=[];previous=None
for row in rows:
    if row.get('mission')!=previous and row.get('mission'):
        changes.append([row['stamp'],row['mission']]);previous=row['mission']
    if row.get('mission')!='RETURN_GATE_SEARCH':continue
    d=row.get('banner_detail',{});t=d.get('capture_stamp')
    if t is None or t in seen:continue
    seen.add(t)
    pose=row.get('pose',{}).get('data',{}).get('pose',{})
    if not pose:continue
    xyz=pose['position'];q=pose['orientation']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    regions=[dict(px=r[:4],area=r[4]) for r in d.get('green_regions',[])]
    if not regions:continue
    mav=SimpleNamespace(banner_green=dict(t=t,wh=d['image_wh'],regions=regions),
        camera_state=row['camera_state'],pos=lambda:(xyz['x'],xyz['y'],xyz['z']),
        alt=lambda:xyz['z'],yaw=lambda:yaw,_scan=None)
    f=green_fix(mav,.851919)
    captures.append(dict(stamp=row['stamp'],capture_stamp=t,identified=d.get('identified'),
        green_regions=d.get('green_regions'),fix=f,camera=row['camera_state'],pose=pose,
        pose_basis='recorded snapshot pose, not capture interpolation'))
review=dict(accepted_source=False,phase_changes=changes,distinct_recorded_green_captures=captures,
    evidence_limit='Snapshots and winch-arrival rows omit intermediate 20 Hz captures; no full-rate negative identity claim. Green replay uses snapshot pose and no lidar, so fixes are diagnostic approximations.',
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'stack.log',run/'configuration.json']})
(run/'return_search_latency_diagnosis.json').write_text(json.dumps(review,indent=2))
whole=[c for c in captures if c['fix'] and not c['fix']['cut'] and not c['fix']['edge']
    and any(1<r[0] and 1<r[1] and r[0]+r[2]<1279 and r[1]+r[3]<719 for r in c['green_regions'])]
print(json.dumps(dict(phase_changes=[c for c in changes if c[0]>635],
    first_whole_candidates=[{k:c[k] for k in ['stamp','green_regions','fix']} for c in whole[:8]]),indent=2))
