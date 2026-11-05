"""Minimise a recorded onboard routing failure without changing the planner."""
import json
import math
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.leg_router import LegRouter
rows = [json.loads(line) for line in (root/'logs/reliability_capture_inbox_field23_navigation_20261007/my_world_field_s2/onboard.jsonl').open()]
row = min(rows, key=lambda row: abs(row['stamp']-450.1))
pose = row['pose']['data']['pose']['position']
class Mav:
    def pos(self): return tuple(pose[k] for k in ('x','y','z'))
    def reached(self,x,y,z,tol): return math.dist(self.pos(), (x,y,z)) < tol
    def log(self,*a,**kw): pass
mav = Mav()
def fails(cells):
    mav.exclusions = cells
    router = LegRouter(clearance_m=1.5, tol=.8, lead_m=3.)
    return router.target(mav,21.,8.6,10.) is None and router.blocked_reason == 'active segment violates exclusion clearance'
cells = row['red_timing']['exclusions']
assert fails(cells)
changed = True
while changed:
    changed = False
    for index in range(len(cells)):
        smaller = cells[:index]+cells[index+1:]
        if fails(smaller):
            cells = smaller
            changed = True
            break
result = dict(pose=mav.pos(), exclusions=cells, goal=[21.,8.6,10.], clearance_m=1.5, lead_m=3., original_stamp=row['stamp'])
path = root/'.scratch/simulation-reliability/field2_escape_minimal_20261007.json'
with path.open('x') as handle:
    json.dump(result, handle, indent=2)
print(json.dumps(result, indent=2))
