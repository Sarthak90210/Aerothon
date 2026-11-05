"""Replay the identified camera handoff using saved onboard evidence only."""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.mission_tree import FindReturnBanner
run = root/'logs/reliability_search_escape_field2_navigation_20261007/my_world_field_s2'
rows = [json.loads(line) for line in (run/'onboard.jsonl').open()]
seen = [row for row in rows if row.get('mission') == 'RETURN_GATE_SEARCH' and row.get('banner_detail',{}).get('identified')]
row = seen[-1]
pp = row['pose']['data']['pose']
q = pp['orientation']
yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
detail = row['banner_detail']
zone = json.loads((run/'world_spec.json').read_text())['delivery_zone']
print(json.dumps(dict(stamp=row['stamp'], pose=pp, camera=row['camera_state'], detail=detail, zone=zone), indent=2))
