import json,sys
from pathlib import Path
sys.path.insert(0,'sim')
from qualification_evidence import recorded_disarm,camera_through_disarm
out=Path('logs/reliability_render_return_fcu_velocity_20261006')
rows=[json.loads(line) for line in (out/'onboard.jsonl').read_text().splitlines()]
print(json.dumps(dict(archive=str(out),recorded_disarm=recorded_disarm(rows),camera_through_disarm=camera_through_disarm(out,rows),note='Read-only evidence crosscheck; archived source qualification is unchanged'),indent=2))