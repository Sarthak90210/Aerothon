"""Real router replay using recorded onboard pose and observed exclusions only."""
import json
import math
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.leg_router import LegRouter
from mission_bt.search_planner import routing_obstacles, path_hits_exclusion

path = root/'logs/reliability_capture_inbox_field23_navigation_20261007/my_world_field_s2/onboard.jsonl'
rows = [json.loads(line) for line in path.open()]
row = min(rows, key=lambda row: abs(row['stamp']-450.1))
pose = row['pose']['data']['pose']['position']
class Mav:
    exclusions = row['red_timing']['exclusions']
    def pos(self): return tuple(pose[k] for k in ('x','y','z'))
    def reached(self,x,y,z,tol): return math.dist(self.pos(), (x,y,z)) < tol
    def log(self,*a,**kw): pass

if '--candidate' in sys.argv:
    from search_escape_candidate_20261007 import install
    install(LegRouter)
router = LegRouter(clearance_m=1.5, tol=.8, lead_m=3.)
target = router.target(Mav(),21.,8.6,10.)
px, py = Mav().pos()[:2]
blocks = routing_obstacles(Mav.exclusions, 1.5)
containing = [r for r in blocks if r[0] <= px <= r[1] and r[2] <= py <= r[3]]
print('containing blocks', containing)
print('escape safe', router._segment_safe(Mav(), router._wps[0]))
print(json.dumps(dict(stamp=row['stamp'], pose=Mav().pos(), exclusions=len(Mav.exclusions),
    planned_waypoints=router._wps, target=target, reason=router.blocked_reason), indent=2))
assert target is not None, 'Recorded field-2 search cannot command its planned exclusion escape'
