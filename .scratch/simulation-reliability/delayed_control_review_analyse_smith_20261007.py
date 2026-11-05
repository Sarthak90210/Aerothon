import json
from pathlib import Path
import sys

path=Path(sys.argv[1])
report=json.loads(path.read_text())
rows=report['rows']
previous=None
for row in rows:
    detail=row['detail']
    mode=(detail.get('diagnostic_mode'),detail.get('braking_clearance_available'),
          detail.get('hold_source'),detail.get('state'))
    if mode!=previous or row['independent_clearance_m']<.70 and previous is not None:
        print(json.dumps(dict(stamp=row['stamp'],pose=row['pose'],clearance=row['independent_clearance_m'],
            mode=mode,command=[detail['cmd_vx'],detail['cmd_vy_left']],
            wind=detail.get('disturbance_world_mps'),rate=detail.get('diagnostic_observer',{}).get('causal_rate_world_mps2'),
            path=detail.get('planner_path_body_m'))))
    previous=mode
