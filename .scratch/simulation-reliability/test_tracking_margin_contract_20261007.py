"""Steering reserve must never weaken the original motion/recovery clearance."""
from rclpy.parameter import Parameter
from test_corridor_clearance_contract import controller
from test_local_planner import wall_scan


def observe(c, left):
    c._planner.observe(*wall_scan(left, 1.75))
    c._axis = c._yaw = 0.
    c._pos = (0., 0.)


def test_tracking_reserve_refuses_steering_with_only_minimum_room(controller):
    c, _ = controller
    observe(c, .74)
    base = c._planner
    assert base.segment_clear((0., 0.), (.1, 0.))
    assert c._local_path(0.) == []
    assert c._planner is base
    assert base.clearance == .70


def test_cached_hint_cannot_bypass_tracking_reserve(controller):
    c, _ = controller
    observe(c, .74)
    c._path_world = [(1., 0.)]
    c._plan_t = c._now()
    assert c._local_path(0.) == []


def test_roomy_observed_path_remains_connected(controller):
    c, _ = controller
    observe(c, .85)
    path = c._local_path(0.)
    assert len(path) > 1
    assert all(c._planner.segment_clear(a,b) for a,b in zip(path,path[1:]))


def test_zero_extra_reserve_still_enforces_full_minimum(controller):
    c, _ = controller
    c.set_parameters([Parameter('path_tracking_margin_m', value=0.)])
    observe(c, .71)
    assert c._local_path(0.) == []
