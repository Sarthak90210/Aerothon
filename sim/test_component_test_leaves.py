#!/usr/bin/env python3
"""GCS testing options: when "Mechanism only" is done, and where the
transmitter test may put the height target.

gcs_testing_20261025 (world-maker simulation, every option from the pad):

  * stow reported Completed 2 s after Start while /winch/status still showed
    the line 5.7 m out and reeling in: the first status after the command was
    the IDLE from before it, which the leaf accepted as done;
  * the transmitter test clamped its height target at 1.0 m, the airborne
    floor the takeoff armed, so a 6 cm sag there ended the test.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_component_test_leaves.py -v
"""
import os
import sys
import time
from types import SimpleNamespace as NS

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_runtime"))
pytest.importorskip("py_trees")
import aerothon_runtime.execution_node as ex  # noqa: E402

S = ex.S


class FakeMav:
    def __init__(self):
        self.commands, self.winch_status, self.abort_requested = [], {}, False
        self.node = NS(remote=False)
        self.airborne_floor = None
        self.abort_reason = ""

    def winch(self, action):
        self.commands.append(action)

    def winch_status_fresh(self):
        return True


def mechanism(action):
    mav = FakeMav()
    leaf = ex.Mechanism(mav, action)
    assert leaf.update() == S.RUNNING           # sends the command
    assert mav.commands == [action]
    return mav, leaf


def test_stow_is_not_done_on_the_idle_from_before_the_command():
    mav, leaf = mechanism("stow")
    mav.winch_status = {"state": "IDLE", "payout_estimate_m": 5.929}
    assert leaf.update() == S.RUNNING
    mav.winch_status = {"state": "STOWING", "payout_estimate_m": 5.7}
    assert leaf.update() == S.RUNNING
    # The measured line settles a few cm out once the FC stops (SITL 0.077 m);
    # the winch counts that as stowed (stow_window_m 0.15).
    mav.winch_status = {"state": "IDLE", "payout_estimate_m": 0.077}
    assert leaf.update() == S.SUCCESS


def test_stow_of_a_line_already_home_is_done():
    mav, leaf = mechanism("stow")
    mav.winch_status = {"state": "IDLE", "payout_estimate_m": 0.0}
    assert leaf.update() == S.SUCCESS


def test_lower_is_done_at_the_limit_not_on_idle():
    mav, leaf = mechanism("lower")
    mav.winch_status = {"state": "IDLE", "payout_estimate_m": 0.0}
    assert leaf.update() == S.RUNNING
    mav.winch_status = {"state": "AT_LIMIT", "payout_estimate_m": 5.929}
    assert leaf.update() == S.SUCCESS


RC = {"forward": {"channel": 2, "min": 1000, "max": 2000, "trim": 1500, "reversed": True},
      "left": {"channel": 1, "min": 1000, "max": 2000, "trim": 1500, "reversed": True},
      "yaw": {"channel": 4, "min": 1000, "max": 2000, "trim": 1500, "reversed": True},
      "climb": {"channel": 3, "min": 1000, "max": 2000, "trim": 1500},
      "takeover": {"channel": 7, "min": 1000, "max": 2000, "active_above": 1800},
      "max_speed": 0.8, "max_yaw_rate": 0.5, "max_climb_rate": 0.5}


def pilot_owner(throttle_us, floor):
    owner = NS(rc_seen=time.monotonic(), rc_config=RC, params={"search_alt": 10.0},
               rc=NS(channels=[1500, 1500, throttle_us, 1500, 1000, 1000, 1000, 1000]),
               mav=FakeMav(), intents=[])
    owner.mav.airborne_floor = floor
    owner.external_intent = lambda vector, height: owner.intents.append(height)
    owner.takeover = lambda reason: None
    return owner


def test_low_throttle_stops_above_the_airborne_floor():
    owner = pilot_owner(1000, floor=1.0)         # throttle held at rest: descend
    leaf = ex.Pilot(owner, 1.3)
    for _ in range(40):
        leaf.previous -= 0.2                     # 0.2 s per tick
        assert leaf.update() == S.RUNNING
    assert owner.intents[-1] == pytest.approx(1.0 + ex.Pilot.FLOOR_MARGIN_M)
    assert min(owner.intents) > owner.mav.airborne_floor


def test_a_test_height_at_the_floor_is_raised_clear_of_it():
    owner = pilot_owner(1500, floor=1.0)         # sticks centred
    leaf = ex.Pilot(owner, 1.0)
    leaf.update()
    assert owner.intents[-1] == pytest.approx(1.0 + ex.Pilot.FLOOR_MARGIN_M)


def test_centred_throttle_holds_the_requested_height():
    owner = pilot_owner(1500, floor=1.0)
    leaf = ex.Pilot(owner, 2.0)
    for _ in range(10):
        leaf.previous -= 0.2
        leaf.update()
    assert owner.intents[-1] == pytest.approx(2.0)
