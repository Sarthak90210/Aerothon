import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'src/aerothon_mission/mission_bt'), str(root/'sim')]
from mission_bt.leg_router import LegRouter
if '--candidate' in sys.argv:
    from search_escape_candidate_20261007 import install
    install(LegRouter)
import pytest
raise SystemExit(pytest.main(['-q', str(root/'sim/test_search_escape_lookahead.py'),
    str(root/'sim/test_leg_routing.py'), str(root/'sim/test_search_planner.py')]))
