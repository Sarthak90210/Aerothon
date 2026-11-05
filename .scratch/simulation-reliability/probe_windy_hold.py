"""Replay one actual stress fixture and retain command evidence offline."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'sim'))
import test_corridor_stress as stress
case = stress.SplitLaneStressTests('test_gusty_crosswind')
case.setUpClass()
case.setUp()
rows = []
original = case.node._publish
segment = case.node._planner.segment_clear
failures = []
def check(start,end):
    result=segment(start,end)
    if not result:
        failures.append(dict(start=list(start),end=list(end),
            known=case.node._planner.known([start,end]).tolist(),
            distances=case.node._planner.distances([start,end]).tolist()))
    return result
def capture(*args, **kwargs):
    failures.clear()
    case.node._planner.segment_clear=check
    original(*args, **kwargs)
    case.node._planner.segment_clear=segment
    rows.append(dict(t=case.node._now(), pose=case.node._pos,
                     desired=args[:2], detail=case.node.last_detail, rejected_segments=list(failures)))
case.node._publish = capture
try:
    seed=int(sys.argv[1]) if len(sys.argv)>1 else 0
    options=dict(corrupt=stress.dirty_lidar(seed)) if 'dirty' in sys.argv[2:] else {}
    case._through(drift=stress.WindDrift(seed=seed),**options)
except AssertionError as exc:
    print(str(exc))
finally:
    (ROOT/'logs/windy_hold_probe.json').write_text(json.dumps(rows))
    print('records', len(rows))
    case.tearDown()
    case.tearDownClass()
