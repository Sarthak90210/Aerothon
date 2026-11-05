"""A nanosecond clock's exact 0.30 s interval must remain admissible."""
from unittest.mock import patch
from test_gate_braking import actor
from mission_bt.mission_tree import GateAdvance
from mission_bt.gate_braking import RUNNING


def test_exact_gate_capture_boundary_does_not_become_a_float_gap():
    mav,leaf=actor();mav.t=682.02;mav.observe();leaf._started=mav.t
    with patch.object(GateAdvance,'update',return_value=RUNNING):
        leaf.update()
    leaf._phase='BRAKE';leaf._brake_hold=mav.xyz;leaf._brake_yaw=0.
    leaf._brake_motion_previous=mav.ground_velocity_samples[-1]
    leaf._brake_capture_stamp=leaf._brake_motion_previous[0]
    mav.t=682.32;mav.observe()
    assert leaf._brake_position(), 'exactly 300000000 ns is not beyond the 0.30 s freshness limit'
