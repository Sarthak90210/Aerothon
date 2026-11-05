"""Test production search code before and with the isolated braking gate."""
import inspect
import json
import sys
import textwrap
from pathlib import Path
import pytest

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'src/aerothon_mission/mission_bt'), str(root/'sim')]
from mission_bt.mission_tree import LawnmowerSearch
variant = sys.argv[1]
assert variant in ('before', 'after', 'regressions')
out = root/('logs/reliability_search_braking_'+variant+'_20261007')
out.mkdir(exist_ok=False)
original = textwrap.dedent(inspect.getsource(LawnmowerSearch.update))
(out/'original_update.py').write_text(original)
candidate = original.replace("    if self.plan is None:\n", "    if not hasattr(self,'_search_braking_gate'):\n        self._search_braking_gate = SearchBrakingGate()\n    if self._search_braking_gate.tick(self):\n        return py_trees.common.Status.RUNNING\n    if self.plan is None:\n")
old = '        status = self.router.fly(self.mav, wx, wy, self.alt, yaw)'
assert candidate.count(old) == 1
candidate = candidate.replace(old, '        self._streamed_search_goal = command[:2]\n'+old)
assert candidate != original
(out/'candidate_update.py').write_text(candidate)
if variant != 'before':
    from search_braking_candidate_20261007 import SearchBrakingGate
    namespace = dict(LawnmowerSearch.update.__globals__, SearchBrakingGate=SearchBrakingGate)
    exec(compile(candidate, str(out/'candidate_update.py'), 'exec'), namespace)
    LawnmowerSearch.update = namespace['update']
tests = [str(Path(__file__).with_name('test_search_braking_20261007.py'))]
if variant == 'regressions':
    tests += [str(root/'sim'/name) for name in ('test_detector_timing.py', 'test_leg_routing.py', 'test_search_planner.py')]
code = pytest.main(['-q', *tests])
(out/'report.json').write_text(json.dumps(dict(variant=variant, exit_code=int(code), production_modified=False,
    physical_flight_qualified=False, scope='Actual search update and emitted commands; scripted onboard motion captures'))+'\n')
raise SystemExit(code)
