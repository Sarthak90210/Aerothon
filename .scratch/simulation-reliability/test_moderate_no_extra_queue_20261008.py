"""Real closed-loop moderate-wind regression with normal actuator response."""
import sys
from pathlib import Path
import pytest
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_avoidance/avoidance')]
import test_corridor_stress as stress


@pytest.mark.parametrize('seed',[0,1,2])
def test_moderate_split_lane_without_injected_control_delay(seed):
    case=stress.SplitLaneStressTests('test_gusty_crosswind')
    case.setUpClass();case.setUp()
    try:case._through(drift=stress.WindDrift(mean=4.,gust=2.,seed=seed),command_delay_s=0.)
    finally:case.tearDown();case.tearDownClass()
