"""Component checks: observation coverage preserved, no hidden gate coordinates."""
import collections,json,math,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.mission_tree import FindReturnBanner
from return_vantage_order_candidate_20261007 import adjacent_observation_order,route_length
from types import SimpleNamespace
results=[]
for zone,origin in [((23.,53.,-2.,24.),(34.4,-.3)),((23.,47.,-26.,-2.),(20.7,-3.25)),
                    ((-53.,-23.,-24.,2.),(-34.4,.3))]:
    obj=object.__new__(FindReturnBanner)
    obj.mav=SimpleNamespace(delivery_search_zone=lambda inset:zone,corridor_exit_pose=(*origin,3.))
    obj.inset_m=3.;obj.here=origin;obj.spacing_m=8.;obj.max_vantages=16
    original=obj._perimeter_vantages();ordered=adjacent_observation_order(origin,original)
    assert collections.Counter(original)==collections.Counter(ordered)
    assert original[0]==ordered[0]
    assert route_length(origin,ordered)<=route_length(origin,original)+1e-9
    assert ordered==adjacent_observation_order(origin,original)
    results.append(dict(zone=zone,observer=origin,viewpoints=len(original),
        original_distance_m=route_length(origin,original),candidate_distance_m=route_length(origin,ordered)))
report=dict(scope='Observation route component; flight paths still require LegRouter clearance checks',
    coverage_preserved=True,pass_component=True,flight_qualified=False,cases=results)
target=root/'logs/reliability_return_vantage_order_candidate_20261007.json'
with target.open('x') as h:json.dump(report,h,indent=2)
print(json.dumps(report,indent=2))
