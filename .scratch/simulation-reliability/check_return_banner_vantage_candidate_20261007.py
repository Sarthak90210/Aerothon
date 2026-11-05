"""Reproduce the first rejected sighting using only recorded drone observations."""
import json,math,sys
from pathlib import Path
import py_trees
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from test_return_gate_search import World,Clock
from mission_bt.mission_tree import FindReturnBanner
from return_banner_vantage_candidate_20261007 import ObservedVantageReturnBanner

zone=(23.,53.,-2.,24.)
view=(34.4,-.3,0.)
seen=(27.3,-11.4)
bearing=math.atan2(seen[1]-view[1],seen[0]-view[0])
distance=math.dist(view[:2],seen)
mav=World([],zone=zone,start=view)
old=FindReturnBanner(mav,clock=Clock()); old.initialise()
assert old._found(*seen,bearing,distance) is None
leaf=ObservedVantageReturnBanner(mav,clock=Clock()); leaf.initialise()
assert leaf._found(*seen,bearing,distance)==py_trees.common.Status.RUNNING
assert leaf.target[:2]==view[:2]
assert leaf.phase=='approach'
assert leaf.update()==py_trees.common.Status.SUCCESS
assert all(math.dist(position,view[:2])<1e-9 for position in mav.path)

# A camera vantage outside the zone side receives the original rejection.
mav=World([],zone=zone,start=(34.4,-10.,0.))
outside=ObservedVantageReturnBanner(mav,clock=Clock()); outside.initialise()
assert outside._found(*seen,bearing,distance) is None

# The fallback does not make a clipped board or the outbound board eligible.
mav=World([(27.3,-11.4,math.pi/2)],zone=zone,start=(*view[:2],bearing))
mav._look()
leaf=ObservedVantageReturnBanner(mav,clock=Clock()); leaf.initialise()
mav.banner_clipped=True
assert leaf._sighting() is None
mav.banner_clipped=False
mav.outbound_banner_xy=seen
assert leaf._sighting() is None
result=dict(scope='Recorded sighting admission and held-pose checks; no native flight qualification',
    baseline_rejected=True,candidate_retains_measured_vantage=True,
    outside_vantage_rejected=True,clipped_and_outbound_rejected=True,
    measurements=dict(observer_xy=view[:2],area_derived_board_xy=seen,organiser_zone=zone),
    simulator_truth_used_by_candidate=False)
with (root/'logs/reliability_return_banner_vantage_candidate_20261007.json').open('x') as handle:
    json.dump(result,handle,indent=2)
print(json.dumps(result))
