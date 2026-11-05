"""Inspect onboard return decisions; never inject simulator truth."""
import json, math, sys
from pathlib import Path
out=Path(sys.argv[1])
last=-1
for line in (out/'onboard.jsonl').open():
    r=json.loads(line);t=r['stamp'];d=r.get('avoidance') or {}
    if r.get('mission')!='RETURN_CORRIDOR' or t-last<.45:continue
    last=t;p=r['pose']['data']['pose'];q=p['orientation'];v=r['velocity']['data']['twist']['linear']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    print(json.dumps(dict(t=t,xy=[p['position']['x'],p['position']['y']],yaw=yaw,state=d.get('state'),clearance=d.get('observed_clearance_m'),
        command=[d.get('cmd_vx'),d.get('cmd_vy_left')],ground=d.get('ground_velocity_world_mps'),fcu=[v['x'],v['y']],wind=d.get('disturbance_world_mps'),rate=d.get('disturbance_rate_world_mps2'),
        path=d.get('planner_path_body_m'),braking=d.get('braking_clearance_available'),hold=d.get('hold_source'),reason=d.get('planner_state'))))
