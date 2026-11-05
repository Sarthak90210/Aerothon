"""Keep frozen-clock physical fixtures distinct from live computation latency."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
import pytest
from rclpy.parameter import Parameter
class Fixtures:
    def pytest_collection_modifyitems(self,items):
        for name in ('test_altitude_hold','test_corridor_yaw_alignment'):
            module=sys.modules[name];original=module.make_controller
            def fresh(factory=original):
                c=factory();c._now=lambda:1.;c._pose_t=c._scan_t=1.
                return c
            module.make_controller=fresh
        module=sys.modules['test_frame_conventions']
        old=module.FrameConventionTests.setUp
        def frame(case):
            old(case);case.node._scan_t=case.node._now()
        module.FrameConventionTests.setUp=frame
        module=sys.modules['test_slalom_traverse']
        old_slalom=module.SlalomTraverseTests.setUp
        def slalom(case):
            old_slalom(case)
            case.node.set_parameters([Parameter('motion_computation_budget_s',value=0.)])
        module.SlalomTraverseTests.setUp=slalom
raise SystemExit(pytest.main(['sim/test_altitude_hold.py','sim/test_corridor_yaw_alignment.py',
    'sim/test_frame_conventions.py','sim/test_corridor_stress.py','-q'],plugins=[Fixtures()]))
