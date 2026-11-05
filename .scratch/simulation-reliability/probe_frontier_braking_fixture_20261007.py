"""Distinguish absent simulated FCU captures from search coverage regressions."""
import json
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'sim'), str(root/'src/aerothon_mission/mission_bt')]
from test_fail_closed_stages import FrontierSearchTests
from mission_bt.search_braking import SearchBrakingGate

original_tick = SearchBrakingGate.tick
records = []
mode = sys.argv[1]

def probe(self, stage):
    if mode == 'fresh':
        now = getattr(stage, '_fixture_now', 0.) + .1
        stage._fixture_now = now
        stage.clock_fn = lambda: stage._fixture_now
        # This existing fixture teleports to commanded poses, so its
        # simulated aircraft is stationary at the start of each tick.
        stage.mav.delivery_inputs = dict(pose_stamp=now, velocity_stamp=now, speed=0.)
    result = original_tick(self, stage)
    if self.hold is not None and len(records) < 4:
        records.append(dict(hold=self.hold, clock_present=callable(stage.clock_fn),
            captures=getattr(stage.mav, 'delivery_inputs', {}), settled=self.settled_samples))
    return result

SearchBrakingGate.tick = probe
names = ('test_red_lane_end_clips_the_lane_instead_of_dropping_it',
         'test_waypoint_turned_red_between_replans_is_replanned_not_skipped')
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(FrontierSearchTests(n) for n in names))
print(json.dumps(dict(mode=mode, tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), observations=records)))
raise SystemExit(0 if result.wasSuccessful() else 1)
