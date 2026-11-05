"""Exercise the real headless setpoint callback and flight-control selection."""
from collections import deque
from types import SimpleNamespace
import threading
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'sim'))
from headless_world import HeadlessWorld


def world(delay=.4):
    w = HeadlessWorld.__new__(HeadlessWorld)
    w.lock = threading.Lock()
    w.mode = 'GUIDED'
    w.armed = True
    w.t = 1.
    w.yaw = 0.
    w.sp_pos = w.sp_vel = w.takeoff_alt = None
    w.args = SimpleNamespace(vel_command_delay_s=delay)
    w.pending_velocity = deque()
    return w


def send(w, vx):
    w._on_sp_raw(SimpleNamespace(velocity=SimpleNamespace(x=vx, y=0., z=0.),
                               yaw_rate=0.))


def desired(w, stamp):
    w.t = stamp
    return w._desired_velocity(np.array([0., 0., 2.]))[0][0]


def test_command_waits_for_transport():
    w = world()
    send(w, .8)
    assert desired(w, 1.2) == 0.
    assert desired(w, 1.4) == pytest.approx(.8)


def test_stop_cannot_cancel_a_command_already_in_transit():
    w = world()
    send(w, .8)
    w.t = 1.2
    send(w, 0.)
    assert desired(w, 1.45) == pytest.approx(.8)
    assert desired(w, 1.65) == 0.


def test_explicit_zero_delay_preserves_immediate_model():
    w = world(0.)
    send(w, .8)
    assert desired(w, 1.) == pytest.approx(.8)
