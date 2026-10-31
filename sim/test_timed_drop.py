#!/usr/bin/env python3
"""The timed drop: WinchDrop without a load calibration (31 Oct 2026).

The aircraft has no loaded/unloaded hover calibration, so the observer would
refuse the delivery at once and the mission would fail into an FC recovery
with the payload on the hook. Uncalibrated, WinchDrop lowers to the ground
plus slack, holds for the gravity hook, winds the line back up and records
the delivery as unconfirmed. A calibrated aircraft keeps the observer.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_timed_drop.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import py_trees                                              # noqa: E402

from mission_bt.mission_tree import WinchDrop                # noqa: E402
from mission_bt.delivery_observer import calibration        # noqa: E402
from test_fail_closed_stages import FakeMav                  # noqa: E402

S = py_trees.common.Status


class Clock:
    def __init__(self):
        self.t = 100.0

    def get_clock(self):
        return self

    def now(self):
        return self

    @property
    def nanoseconds(self):
        return int(self.t * 1e9)


class Winch:
    """winch_ctrl's l298n estimate: 0.30 m/s, 6 m line, AT_LIMIT, IDLE."""

    def __init__(self, line=6.0, rate=0.30):
        self.line, self.rate = line, rate
        self.payout, self.state, self.commands = 0.0, "IDLE", []

    def command(self, cmd):
        self.commands.append(cmd)
        if cmd == "lower" and self.state not in ("LOWERING", "AT_LIMIT"):
            self.state = "LOWERING"
        elif cmd == "stow":
            self.state = "STOWING"
        elif cmd == "stop" and self.state in ("LOWERING", "STOWING", "AT_LIMIT"):
            self.state = "IDLE"

    def advance(self, dt):
        if self.state == "LOWERING":
            self.payout = min(self.line, self.payout + self.rate * dt)
            if self.payout >= self.line:
                self.state = "AT_LIMIT"
        elif self.state == "STOWING":
            self.payout = max(0.0, self.payout - self.rate * dt)
            if self.payout <= 1e-3:
                self.payout, self.state = 0.0, "IDLE"

    def status(self):
        return {"payout_estimate_m": self.payout, "state": self.state, "fault": ""}


def rig(alt=5.0):
    mav = FakeMav()
    mav.node = Clock()
    mav._alt = alt
    mav._pos = (2.0, 3.0, alt)
    winch = Winch()
    mav.winch = winch.command
    mav.winch_status = winch.status()
    mav.winch_status_fresh = lambda: True
    leaf = WinchDrop(mav, drop_alt=5.0, cruise_alt=10.0, winch_reach_m=5.5, marker_m=1.0)
    leaf.initialise()
    leaf.phase = 1
    return mav, winch, leaf


def run(mav, winch, leaf, seconds, dt=0.2):
    status = S.RUNNING
    for _ in range(int(seconds / dt)):
        mav.node.t += dt
        winch.advance(dt)
        mav.winch_status = winch.status()
        status = leaf.update()
        if status != S.RUNNING or leaf.phase == 5:
            return status
    return status


class TimedDropTests(unittest.TestCase):

    def test_uncalibrated_lowers_holds_winds_up_and_climbs_unconfirmed(self):
        mav, winch, leaf = rig()
        self.assertTrue(leaf.timed)
        self.assertEqual(run(mav, winch, leaf, 120), S.RUNNING)
        self.assertEqual(leaf.phase, 5)
        # Lowered to the release height plus the slack, then held stopped.
        self.assertEqual(winch.commands[0], "lower")
        self.assertIn("stop", winch.commands)
        self.assertIn("stow", winch.commands)
        first_stop = winch.commands.index("stop")
        self.assertTrue(all(c == "lower" for c in winch.commands[:first_stop]))
        self.assertGreaterEqual(leaf._timed_payout,
                                leaf.release_alt + leaf.TIMED_SLACK_M - 0.1)
        self.assertEqual(winch.payout, 0.0)
        self.assertFalse(mav.delivery_confirmed)
        self.assertIn("timed drop without load calibration", mav.delivery_note)
        # Then the ordinary climb back.
        mav._pos = (leaf.drop_x, leaf.drop_y, leaf.cruise_alt)
        self.assertEqual(leaf.update(), S.SUCCESS)
        self.assertEqual(mav.modes, [])

    def test_the_hold_lasts_its_full_time_with_the_line_stopped(self):
        mav, winch, leaf = rig()
        run(mav, winch, leaf, 60, dt=0.2)
        start = winch.commands.index("stop")
        stow = winch.commands.index("stow")
        held = winch.commands[start:stow]
        self.assertTrue(all(c == "stop" for c in held))
        self.assertGreaterEqual(len(held) * 0.2, leaf.TIMED_HOLD_S - 0.2)

    def test_the_slack_is_measured_from_the_height_actually_held(self):
        # Rendered 31 Oct: hovering 0.5 m above the release height left the
        # line 0.1 m short of the ground.
        mav, winch, leaf = rig()
        mav._alt = leaf.release_alt + 0.5
        run(mav, winch, leaf, 120)
        self.assertGreaterEqual(leaf._timed_payout,
                                min(winch.line, mav._alt + leaf.TIMED_SLACK_M) - 0.1)
        self.assertGreaterEqual(leaf._timed_payout, mav._alt)

    def test_a_short_line_stops_at_its_limit(self):
        mav, winch, leaf = rig()
        winch.line = 3.0                       # AT_LIMIT before release + slack
        run(mav, winch, leaf, 120)
        self.assertEqual(leaf.phase, 5)
        self.assertAlmostEqual(leaf._timed_payout, 3.0, places=1)

    def test_a_winch_fault_fails_the_drop(self):
        mav, winch, leaf = rig()
        run(mav, winch, leaf, 3)
        mav.winch_status = dict(winch.status(), fault="motor stalled")
        self.assertEqual(leaf.update(), S.FAILURE)
        self.assertFalse(mav.delivery_confirmed)
        self.assertEqual(winch.commands[-1], "stop")

    def test_stale_winch_status_fails_after_its_grace(self):
        mav, winch, leaf = rig()
        run(mav, winch, leaf, 2)
        mav.winch_status_fresh = lambda: False
        status = S.RUNNING
        for _ in range(int((leaf.TIMED_STALE_S + 1) / 0.2)):
            mav.node.t += 0.2
            status = leaf.update()
            if status != S.RUNNING:
                break
        self.assertEqual(status, S.FAILURE)
        self.assertEqual(winch.commands[-1], "stop")

    def test_a_line_that_never_winds_up_fails(self):
        mav, winch, leaf = rig()
        winch.rate = 0.30
        run(mav, winch, leaf, 40)              # lowered and holding/stowing
        winch.rate = 0.0                       # stuck while winding up
        status = run(mav, winch, leaf, leaf.TIMED_STOW_MAX_S + 10)
        self.assertEqual(status, S.FAILURE)
        self.assertIn("winding up timed out", mav.delivery_note)

    def test_a_calibrated_aircraft_keeps_the_observer(self):
        mav = FakeMav()
        mav.delivery_load_profile = calibration([.26] * 40, [.24] * 40)
        leaf = WinchDrop(mav)
        leaf.initialise()
        self.assertFalse(leaf.timed)


if __name__ == "__main__":
    unittest.main()
