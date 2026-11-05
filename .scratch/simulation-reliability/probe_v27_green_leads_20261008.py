"""Replay recorded mixed green regions through the actual range selector."""
import json,math,sys
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.banner_orbit import green_fix
run=root/'logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3';records=[];seen=set()
for line in (run/'onboard.jsonl').open():
 r=json.loads(line);d=r.get('banner_detail') or {};t=d.get('capture_stamp')
 if r.get('mission')!='RETURN_GATE_SEARCH' or t in seen or t is None or t>714:continue
 seen.add(t);p=r['pose']['data']['pose'];xyz=p['position'];q=p['orientation'];yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
 regions=[dict(px=b[:4],area=b[4]) for b in d.get('green_regions',[])]
 if not regions:continue
 mav=SimpleNamespace(banner_green=dict(t=t,wh=d['image_wh'],regions=regions),camera_state=r['camera_state'],pos=lambda:(xyz['x'],xyz['y'],xyz['z']),alt=lambda:xyz['z'],yaw=lambda:yaw,_scan=None)
 f=green_fix(mav,.851919)
 if f and not f['cut'] and not f['edge'] and 2<=f['range']<=15:
  records.append(dict(stamp=r['stamp'],detail=d,camera=r['camera_state'],pose=p,fix=f))
(run/'green_lead_snapshot_replay.json').write_text(json.dumps(dict(records=records,limitation='Snapshot poses and no lidar are approximate, not a full-rate callback reconstruction'),indent=2))
print(json.dumps(records[:5],indent=2))
print('near whole lead snapshots',len(records))
