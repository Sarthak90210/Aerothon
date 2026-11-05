"""Frozen field-2 sighting handoff and face-on control case."""
import json,math,sys
from pathlib import Path
import py_trees
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_mission/mission_bt')]
from test_return_gate_search import World,Clock
from mission_bt.mission_tree import FindReturnBanner
from oblique_observer_return_candidate_20261007 import ObliqueObserverReturnBanner
observer=(24.,-6.,math.radians(-129.))
board=(15.2,-17.)
heading=math.atan2(board[1]-observer[1],board[0]-observer[0])
zone=(17.261,57.261,-20.435,9.565)
original=FindReturnBanner(World([],zone=zone,start=observer),clock=Clock());original.initialise();original._found(*board,heading,13.9)
candidate=ObliqueObserverReturnBanner(World([],zone=zone,start=observer),clock=Clock());candidate.initialise();candidate._found(*board,heading,13.9)
assert math.dist(original.target[:2],observer[:2])>10
assert candidate.target[:2]==observer[:2]
assert candidate.update()==py_trees.common.Status.SUCCESS
assert candidate.mav.gotos[-1][:2]==observer[:2]
# Existing face-on placement is retained when the ray is within 45 degrees.
control=ObliqueObserverReturnBanner(World([],start=(14.5,2.,0.)),clock=Clock());control.initialise();control._found(26.,-18.,math.atan2(-20.,11.5),23.)
assert control.target[:2]==(26.,-13.)
# A viewpoint behind the zone is not made eligible by this candidate.
outside=ObliqueObserverReturnBanner(World([],zone=zone,start=(12.,-25.,0.)),clock=Clock());outside.initialise();baseline_outside=FindReturnBanner(World([],zone=zone,start=(12.,-25.,0.)),clock=Clock());baseline_outside.initialise();expected=baseline_outside._found(*board,heading,13.9)
assert outside._found(*board,heading,13.9)==expected
assert outside.target==baseline_outside.target
assert outside.target[:2]!=(12.,-25.)
report=dict(scope='Recorded onboard sighting/zone-side handoff only; no world truth in candidate; no mission qualification',observer_xy=observer[:2],area_derived_board_xy=board,baseline_target=original.target,candidate_target=candidate.target,face_on_control_preserved=True,outside_observer_not_retained=True)
with (root/'logs/reliability_oblique_observer_handoff_20261007.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps(report))
