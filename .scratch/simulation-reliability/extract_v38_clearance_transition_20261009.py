"""Read the earliest recorded stop transition without changing flight code."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
selected=[]
for row in rows:
    detail=row.get('avoidance',{})
    gap=detail.get('observed_clearance_m')
    if row.get('mission')=='RETURN_CORRIDOR' and isinstance(gap,(int,float)) and gap<.78:
        selected.append(dict(stamp=row['stamp'],state=detail['state'],clearance_m=gap,
            command=[detail.get('cmd_vx'),detail.get('cmd_vy_left')],
            ground=detail.get('ground_velocity_world_mps'),wind=detail.get('disturbance_world_mps'),
            planner=detail.get('planner_state'),recovery=detail.get('recovery_reason')))
(run/'clearance_stop_transition.json').write_text(json.dumps(selected,indent=2))
print(json.dumps(selected[:18],indent=2))
