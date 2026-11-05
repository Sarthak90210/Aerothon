"""Arrival remains physical despite estimator wander and service waits."""
from unittest.mock import patch
import pytest
from test_gate_braking import actor
from mission_bt.mission_tree import GateAdvance
from mission_bt.gate_braking import RUNNING,FAILURE,SUCCESS


def enter():
    mav,leaf=actor()
    with patch.object(GateAdvance,'update',return_value=SUCCESS):
        assert leaf.update() is RUNNING
    return mav,leaf


def test_estimator_jump_is_cancelled_without_flying_to_old_gps_anchor():
    mav,leaf=enter()
    for t,xy in [(1.2,(21.,-17.)),(1.4,(19.,-14.))]:
        mav.t=t;mav.xyz=(*xy,2.);mav.observe()
        status=leaf.update()
        assert mav.commands[-1]==mav.xyz
        assert leaf._brake_displacement==[0.,0.]
    assert status is SUCCESS and mav.speed_requests==[.5,5.]


def test_ground_displacement_is_retained_when_estimate_moves():
    mav,leaf=actor();mav.observe(speed=.4)
    with patch.object(GateAdvance,'update',return_value=SUCCESS):
        assert leaf.update() is RUNNING
    mav.t=1.2;mav.xyz=(21.,-15.,2.);mav.observe(speed=.2)
    assert leaf.update() is RUNNING
    assert leaf._brake_displacement==pytest.approx([.06,0.])
    assert mav.commands[-1]==pytest.approx((20.94,-15.,2.))
    assert mav.speed_requests==[.5]
    previous=leaf._brake_displacement.copy()
    assert leaf.update() is RUNNING
    assert leaf._brake_displacement==previous


@pytest.mark.parametrize('kind',['missing','nan','malformed','gap'])
def test_unusable_vector_history_fails_closed_even_with_fresh_scalar_speed(kind):
    mav,leaf=enter();mav.t=1.2;mav.observe()
    if kind=='missing':mav.ground_velocity_samples.clear()
    if kind=='nan':mav.ground_velocity_samples.append((1.2,float('nan'),0.))
    if kind=='malformed':mav.ground_velocity_samples.append(None)
    if kind=='gap':
        mav.ground_velocity_samples.clear()
        mav.t=1.4;mav.observe()
    assert leaf.update() is FAILURE
    assert mav.commands[-1]==mav.xyz and mav.speed_requests==[.5]
    assert 'continuous fresh ground velocity' in mav.abort_reason


def test_future_vector_cannot_supply_missing_current_motion():
    mav,leaf=enter();mav.t=1.4;mav.observe()
    mav.ground_velocity_samples.clear();mav.ground_velocity_samples.append((2.,0.,0.))
    assert leaf.update() is FAILURE
    assert mav.speed_requests==[.5]


def test_duplicate_captures_cannot_finish_braking_after_estimate_change():
    mav,leaf=enter();mav.xyz=(21.,-18.,2.)
    for _ in range(5):
        mav.t+=.02
        assert leaf.update() is RUNNING
        assert mav.commands[-1]==mav.xyz
    assert leaf._settle_count==1 and mav.speed_requests==[.5]


def test_pending_restore_stays_at_physical_hold_through_estimate_change():
    mav,leaf=enter()
    mav.t=1.2;mav.observe();assert leaf.update() is RUNNING
    mav.t=1.4;mav.observe();mav.response='pending'
    assert leaf.update() is RUNNING and leaf._phase=='RESTORE'
    for t in [1.6,1.8,2.]:
        mav.t=t;mav.xyz=(20.+t,-16.-t,2.);mav.observe()
        assert leaf.update() is RUNNING
        assert mav.commands[-1]==mav.xyz
    assert mav.speed_requests==[.5,5.]


def test_altitude_arrival_tolerance_is_unchanged():
    mav,leaf=enter();leaf.tol=.25;mav.xyz=(20.,-16.,2.7)
    mav.t=1.2;mav.observe();assert leaf.update() is RUNNING
    mav.t=1.4;mav.observe();assert leaf.update() is RUNNING
    assert mav.commands[-1][2]==2. and mav.speed_requests==[.5]
    assert leaf.arrival_speed_mps==.08 and leaf.stale_s==.3
