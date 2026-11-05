"""The real search leaf must brake before it executes a replacement route."""
from types import SimpleNamespace
import pytest
from mission_bt.mission_tree import LawnmowerSearch
from test_leg_routing import RoutedMav


def make_stage():
    mav = RoutedMav(at=(0., 0., 10.))
    now = [1.]
    mav.delivery_inputs = dict(pose_stamp=1., velocity_stamp=1., speed=.6)
    stage = LawnmowerSearch(mav, (-5., 40., -20., 20.), 10.,
                           exclusions=lambda: mav.exclusions, clock=lambda: now[0], crab=True)
    stage.initialise()
    stage.wps = [(30., 0.)]
    stage.i = 0
    stage.update()
    assert mav.gotos[-1][:2] == (30., 0.)
    mav.exclusions = [(10., 20., -5., 5.)]
    return stage, mav, now


def test_new_exclusion_stops_before_replacement_route():
    stage, mav, _ = make_stage()
    stage.update()
    assert mav.gotos[-1][:3] == mav.pos(), 'new exclusion must first cancel the streamed search goal'


def test_braking_target_does_not_chase_the_moving_aircraft():
    stage, mav, _ = make_stage()
    stage.update()
    target = mav.gotos[-1][:3]
    mav._pos = (.2, 0., 10.)
    stage.update()
    assert mav.gotos[-1][:3] == target


def test_duplicate_settled_samples_cannot_resume_search():
    stage, mav, _ = make_stage()
    stage.update()
    mav.delivery_inputs['speed'] = 0.
    for _ in range(10):
        stage.update()
        assert mav.gotos[-1][:3] == (0., 0., 10.)


@pytest.mark.parametrize('bad', ['stale', 'missing', 'future', 'nonfinite'])
def test_unusable_motion_evidence_keeps_search_stopped(bad):
    stage, mav, now = make_stage()
    stage.update()
    mav.delivery_inputs['speed'] = 0.
    if bad == 'stale':
        now[0] = 2.
    elif bad == 'missing':
        del mav.delivery_inputs['velocity_stamp']
    elif bad == 'future':
        mav.delivery_inputs['velocity_stamp'] = 2.
    else:
        mav.delivery_inputs['speed'] = float('nan')
    for _ in range(5):
        stage.update()
        assert mav.gotos[-1][:3] == (0., 0., 10.)


def test_replan_uses_measured_stop_position_after_distinct_samples():
    stage, mav, now = make_stage()
    stage.update()
    replans = []
    original = stage._replan_mid_sweep
    def record():
        replans.append(mav.pos())
        original()
    stage._replan_mid_sweep = record
    mav._pos = (.3, 0., 10.)
    for stamp in (1.1, 1.2, 1.3):
        now[0] = stamp
        mav.delivery_inputs.update(pose_stamp=stamp, velocity_stamp=stamp, speed=.02)
        stage.update()
    assert replans == [(.3, 0., 10.)]
    assert mav.gotos[-1][:3] == (0., 0., 10.)
    stage.update()
    assert mav.gotos[-1][:2] != (30., 0.)
