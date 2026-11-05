"""Lidar loss must stop commands without erasing fresh FCU drift observations."""
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'sim'))
from test_corridor_clearance_contract import controller


def seed_response(c):
    c._pose_t = c._fcu_velocity_t = 1.
    c._fcu_velocity = np.array([.2, -.1])
    c._ground_world = c._fcu_velocity.copy()
    c._wind_world = c._fcu_velocity.copy()
    c._model_t = .9
    c._drift_prev = c._pos
    c._drift_prev_t = .9
    c._expect_world = np.zeros(2)
    c._command_history.append((.8, np.zeros(2)))
    c._response_known = True


def test_lidar_fault_retains_fresh_measured_disturbance(controller):
    c, sent = controller
    seed_response(c)
    c._publish(0., 0., 0., 0., {'fault': 'scan stale or missing'})
    np.testing.assert_allclose(c._wind_world, [.2, -.1], atol=1e-12)
    assert c._response_known
    assert sent[-1].velocity.x == sent[-1].velocity.y == sent[-1].yaw_rate == 0.


def test_repeated_lidar_fault_advances_only_distinct_fcu_samples(controller):
    c, sent = controller
    seed_response(c)
    c._publish(0., 0., 0., 0., {'fault': 'scan stale or missing'})
    first = c._wind_world.copy()
    c._publish(0., 0., 0., 0., {'fault': 'scan stale or missing'})
    np.testing.assert_array_equal(c._wind_world, first)
    assert c._model_t == 1.
    assert len(sent) == 2
    assert all(sp.velocity.x == sp.velocity.y == 0. for sp in sent)


@pytest.mark.parametrize('lost', ['pose', 'velocity', 'invalid_velocity'])
def test_flight_observation_loss_still_invalidates_observer(controller, lost):
    c, sent = controller
    seed_response(c)
    if lost == 'pose':
        c._pose_t = -1.
    elif lost == 'velocity':
        c._fcu_velocity_t = -1.
    else:
        c._velocity_fault = 'invalid FCU velocity'
    c._publish(0., 0., 0., 0., {'fault': 'flight observations unavailable'})
    np.testing.assert_array_equal(c._wind_world, [0., 0.])
    assert not c._response_known
    assert sent[-1].velocity.x == sent[-1].velocity.y == 0.
