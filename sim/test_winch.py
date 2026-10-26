#!/usr/bin/env python3
"""Winch controller: real subscriber, real feedback, gated release.

Before this existed, /winch/cmd had two publishers and zero subscribers, and
WinchDrop "delivered" after a fixed 20-tick timer whether or not anything had
moved. Payload delivery is what Mission 2 scores.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_winch.py -v
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "aerothon_payload", "winch_ctrl"))

import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from std_msgs.msg import String

from winch_ctrl.winch_node import WinchNode


def pose(z):
    m = PoseStamped()
    m.pose.position.z = float(z)
    return m


def vel(vx, vy=0.0):
    m = TwistStamped()
    m.twist.linear.x = float(vx)
    m.twist.linear.y = float(vy)
    return m


class WinchTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not rclpy.ok():
            rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        self.node = WinchNode()
        self.status = []
        self.node.pub_status.publish = self.status.append

    def tearDown(self):
        self.node.destroy_node()

    def cmd(self, text):
        self.node._on_cmd(String(data=text))

    def last(self):
        self.node.publish_status()
        return json.loads(self.status[-1].data)

    def advance(self, seconds, step=0.1):
        n = max(1, int(seconds / step))
        for _ in range(n):
            self.node.integrate(step)

    def stabilise(self, alt=5.0, n=10):
        self.node._on_pose(pose(alt))
        for _ in range(n):
            self.node._on_vel(vel(0.05))

    def lower_to_ground(self, alt=5.0):
        self.stabilise(alt)
        self.cmd("lower")
        for _ in range(400):
            self.node.integrate(0.1)
            if self.node.at_ground() or self.node.at_limit():
                break

    # ---- the interface exists at all ---- #
    def test_publishes_status(self):
        st = self.last()
        self.assertIn("state", st)
        self.assertIn("payout_m", st)
        self.assertEqual(st["state"], "IDLE")

    def test_unknown_command_is_ignored(self):
        self.cmd("banana")
        self.assertEqual(self.node.state, "IDLE")

    # ---- lowering ---- #
    def test_lower_pays_out_line(self):
        self.stabilise(5.0)
        self.cmd("lower")
        before = self.node.payout
        self.advance(2.0)
        self.assertGreater(self.node.payout, before)

    def test_estimated_ground_travel_does_not_claim_ground_contact(self):
        self.lower_to_ground(4.0)
        self.assertEqual(self.node.state, "LOWERING")
        self.assertTrue(self.node.at_ground() or self.node.at_limit())

    def test_payout_never_exceeds_spool(self):
        self.stabilise(50.0)          # unreachable ground
        self.cmd("lower")
        self.advance(120.0)
        self.assertLessEqual(self.node.payout,
                             self.node.get_parameter("max_payout_m").value + 1e-6)

    # ---- the interlocks: the point of the node ---- #
    def test_release_refused_before_payload_is_down(self):
        self.stabilise(5.0)
        self.cmd("release")
        self.assertFalse(self.node.released,
                         "released with the payload still hanging")
        self.assertIn("not down", self.node.fault)

    def test_an_actuated_hook_is_refused_while_drifting(self):
        from rclpy.parameter import Parameter
        self.node.set_parameters([Parameter("hook", Parameter.Type.STRING, "command")])
        self.lower_to_ground(4.0)
        for _ in range(10):
            self.node._on_vel(vel(3.0))      # moving fast
        ok, blockers = self.node.release_ok()
        self.assertFalse(ok)
        self.assertTrue(any("hover" in b for b in blockers), blockers)

    def test_a_gravity_hook_is_not_held_up_by_a_gust(self):
        """The payload is on the ground and off the hook; the wind moving
        the aircraft cannot change that."""
        self.lower_to_ground(4.0)
        self.advance(30.0)
        for _ in range(10):
            self.node._on_vel(vel(3.0))
        ok, blockers = self.node.release_ok()
        self.assertTrue(ok, blockers)

    def test_release_refused_when_too_high(self):
        self.stabilise(50.0)
        self.cmd("lower")
        self.advance(120.0)
        ok, blockers = self.node.release_ok()
        self.assertFalse(ok)
        self.assertTrue(any("altitude" in b for b in blockers), blockers)

    def test_release_succeeds_when_every_condition_holds(self):
        self.lower_to_ground(4.0)
        self.stabilise(4.0)
        ok, blockers = self.node.release_ok()
        self.assertTrue(ok, f"unexpected blockers: {blockers}")
        self.cmd("release")
        self.assertTrue(self.node.released)
        self.assertEqual(self.node.state, "RELEASED")

    def test_cannot_lower_after_release(self):
        self.lower_to_ground(4.0)
        self.stabilise(4.0)
        self.cmd("release")
        self.cmd("lower")
        self.assertIn("already released", self.node.fault)

    def test_delivered_payload_reports_delivery_not_a_fault(self):
        """A successful delivery must not read as a malfunction.

        The first live run left the GCS showing
        `fault: release refused: already released` for the entire return leg,
        after a delivery that had actually succeeded.
        """
        self.lower_to_ground(4.0)
        self.stabilise(4.0)
        self.cmd("release")
        self.assertTrue(self.node.released)
        ok, blockers = self.node.release_ok()
        self.assertFalse(ok)
        self.assertEqual(blockers, ["payload already delivered"])
        self.assertNotIn("fault", " ".join(blockers))

    def test_second_release_is_ignored_without_raising_a_fault(self):
        """Re-commanding release on a delivered payload is redundant, not broken.

        Raising a FAULT here left the GCS reporting an error for the entire
        return leg of a mission whose delivery had succeeded.
        """
        self.lower_to_ground(4.0)
        self.stabilise(4.0)
        self.cmd("release")
        self.assertTrue(self.node.released)
        self.node.fault = ""
        self.cmd("release")
        self.assertEqual(self.node.fault, "",
                         "a redundant release must not raise a fault")
        self.assertEqual(self.node.state, "RELEASED")
        self.assertTrue(self.node.released)

    def test_transient_refusal_clears_once_conditions_are_met(self):
        """A refusal is a condition, not a latched failure."""
        self.stabilise(4.0)
        self.cmd("release")                      # too early: payload not down
        self.assertEqual(self.node.state, "FAULT")
        self.cmd("lower")
        for _ in range(400):
            self.node.integrate(0.1)
            if self.node.at_ground():
                break
        self.stabilise(4.0)
        self.node.integrate(0.1)
        self.assertEqual(self.node.fault, "",
                         "stale refusal still reported after it was resolved")

    def test_ground_release_refusal_does_not_block_stow(self):
        self.stabilise(0.0)
        self.node.payout = 0.6
        self.cmd("release")
        self.assertIn("release refused", self.node.fault)
        self.cmd("stow")
        self.advance(3.0)
        status = self.last()
        self.assertEqual(status["state"], "IDLE")
        self.assertEqual(status["fault"], "", "old release refusal blocked safe stow")
        self.assertFalse(status["release_requested"])
        self.assertIsNone(status["released"])

    def test_ground_release_refusal_does_not_block_stop(self):
        self.stabilise(0.0)
        self.cmd("release")
        self.assertIn("release refused", self.node.fault)
        self.cmd("stop")
        self.assertEqual(self.last()["fault"], "")
        self.assertEqual(self.node.state, "IDLE")
        self.assertFalse(self.node.released)

    def test_release_cannot_replace_a_backend_fault_with_a_transient_refusal(self):
        self.lower_to_ground(4.0)
        self.node._set_fault("encoder stalled")
        self.cmd("release")
        self.node.integrate(0.1)
        self.assertEqual(self.last()["fault"], "encoder stalled")
        self.assertEqual(self.node.state, "FAULT")
        self.assertFalse(self.node.released)

    def test_stop_and_stow_preserve_a_backend_fault(self):
        for action in ("stop", "stow"):
            with self.subTest(action=action):
                self.node._set_fault("encoder stalled")
                self.cmd(action)
                self.node.integrate(0.1)
                self.assertEqual(self.last()["fault"], "encoder stalled")

    def test_blockers_are_reported_not_just_the_first(self):
        """The operator should see everything wrong at once."""
        self.node._on_pose(pose(40.0))
        for _ in range(10):
            self.node._on_vel(vel(5.0))
        ok, blockers = self.node.release_ok()
        self.assertFalse(ok)
        self.assertGreaterEqual(len(blockers), 2, blockers)

    # ---- stow ---- #
    def test_stow_retracts_and_finishes(self):
        self.lower_to_ground(4.0)
        self.cmd("stow")
        for _ in range(1000):
            self.node.integrate(0.1)
            if self.node.payout <= 0.0:
                break
        self.assertEqual(self.node.payout, 0.0)
        self.assertIn(self.node.state, ("IDLE", "RELEASED"))

    def test_status_reports_release_ok_and_blockers(self):
        st = self.last()
        self.assertIn("release_ok", st)
        self.assertIn("blockers", st)
        self.assertFalse(st["release_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class FakeFuture:
    def __init__(self):
        self.callbacks, self.reply = [], None

    def add_done_callback(self, cb):
        self.callbacks.append(cb)

    def result(self):
        return self.reply

    def finish(self, success=True, result=0):
        from types import SimpleNamespace
        self.reply = SimpleNamespace(success=success, result=result)
        for cb in self.callbacks:
            cb(self)


class FakeCommandClient:
    def __init__(self, ready=True):
        self.ready, self.sent = ready, []

    def service_is_ready(self):
        return self.ready

    def call_async(self, req):
        f = FakeFuture()
        self.sent.append((req, f))
        return f


class MavlinkWinchTests(unittest.TestCase):
    """16 Oct audit: on the default mavlink backend the payout estimate grew
    while nothing moved (command unsent or refused), and at 0.30 m/s while
    ArduPilot's length control reeled at WNCH_RATE_MAX (1.0 m/s)."""

    @classmethod
    def setUpClass(cls):
        cls.owns = not rclpy.ok()
        if cls.owns:
            rclpy.init()

    @classmethod
    def tearDownClass(cls):
        if cls.owns and rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        from rclpy.parameter import Parameter
        self.node = WinchNode(parameter_overrides=[
            Parameter("backend", Parameter.Type.STRING, "mavlink"),
            Parameter("fc_rate_max_mps", Parameter.Type.DOUBLE, 0.30)])
        self.node.pub_status.publish = lambda *_: None
        self.client = FakeCommandClient()
        self.node.cli_cmd = self.client
        self.node._on_pose(pose(5.0))
        self.fc_winch(1, 0.30)          # read back from the FC, as MAVROS reports it

    def fc_winch(self, wtype, rate):
        from rcl_interfaces.msg import ParameterValue
        self.node.on_fc_winch_params([ParameterValue(type=2, integer_value=wtype),
                                      ParameterValue(type=3, double_value=rate)])

    def measure(self, metres):
        self.node.measured_payout = metres
        self.node._measurement_t = self.node._now()

    def tearDown(self):
        self.node.destroy_node()

    def advance(self, seconds, step=0.1):
        for _ in range(int(seconds / step)):
            self.node.integrate(step)

    def test_no_payout_until_the_fc_accepts(self):
        self.node._on_cmd(String(data="lower"))
        self.advance(2.0)
        self.assertEqual(self.node.payout, 0.0, "estimate grew with nothing accepted")
        self.client.sent[-1][1].finish()
        self.advance(2.0)
        self.assertAlmostEqual(self.node.payout, 0.60, places=2)   # FC's rate

    def test_a_refused_command_is_a_fault(self):
        self.node._on_cmd(String(data="lower"))
        self.client.sent[-1][1].finish(success=False, result=3)    # UNSUPPORTED
        self.assertEqual(self.node.state, "FAULT")
        self.assertIn("refused DO_WINCH lower", self.node.fault)

    def test_an_unsent_command_is_a_fault(self):
        self.client.ready = False
        self.node._on_cmd(String(data="lower"))
        self.assertEqual(self.node.state, "FAULT")
        self.assertEqual(self.client.sent, [])

    # ---- 20 Oct 2026: the hook dragged through the return corridor ---- #
    # The laptop simulator's FC reeled at WINCH_RATE_MAX 1.0 while the estimate
    # assumed 0.30; stow by the estimate left 2.6 m out (measured winch joint),
    # the hook snagged, and the aircraft stalled, tilted and sank.

    def test_lowering_is_refused_until_the_fc_winch_is_read_back(self):
        self.node.fc_winch = None
        self.node._on_cmd(String(data="lower"))
        self.assertEqual(self.node.state, "FAULT")
        self.assertIn("not read back", self.node.fault)
        self.assertEqual(self.client.sent, [])

    def test_a_disabled_fc_winch_is_refused(self):
        self.fc_winch(0, 0.30)          # e.g. WNCH_TYPE set on a 4.5 FC: WINCH_TYPE stays 0
        self.node._on_cmd(String(data="lower"))
        self.assertIn("winch disabled", self.node.fault)

    def test_the_estimate_uses_the_fc_rate_not_the_configured_one(self):
        self.fc_winch(1, 1.0)
        self.node._on_cmd(String(data="lower"))
        self.client.sent[-1][1].finish()
        self.advance(2.0)
        self.assertAlmostEqual(self.node.payout, 2.0, places=2)
        self.node._on_cmd(String(data="stow"))
        self.assertAlmostEqual(self.client.sent[-1][0].param3, -2.0, places=2)

    def test_stow_is_not_reported_while_the_measured_line_is_still_out(self):
        self.node._on_cmd(String(data="lower"))
        self.client.sent[-1][1].finish()
        self.measure(3.4)
        self.node.integrate(0.1)
        self.node._on_cmd(String(data="stow"))
        self.client.sent[-1][1].finish()
        self.assertAlmostEqual(self.client.sent[-1][0].param3, -3.4, places=2)
        for _ in range(10):             # the FC reeled in only part of it
            self.measure(2.6)
            self.node.integrate(0.1)
        self.assertEqual(self.node.state, "STOWING")
        self.assertAlmostEqual(self.node.payout, 2.6)

    def test_a_stalled_stow_is_resent_by_the_measured_length(self):
        self.node._on_cmd(String(data="stow"))
        sent = len(self.client.sent)
        for _ in range(25):             # 2.5 s, no progress
            self.measure(2.6)
            self.node.integrate(0.1)
        self.assertEqual(len(self.client.sent), sent + 1)
        self.assertAlmostEqual(self.client.sent[-1][0].param3, -2.6, places=2)
        self.client.sent[-1][1].finish()
        for m in (2.0, 1.2, 0.5, 0.1):
            self.measure(m)
            self.node.integrate(0.5)
        self.assertEqual(self.node.state, "IDLE")
        self.assertEqual(self.node.payout, 0.0)

    # ---- 25 Oct 2026: a bench "lower" never finished in simulation ---- #
    # The FC's length control settled 7 cm short of the length it was sent
    # (measured 5.929 of max_payout_m 6.0) and the node stayed LOWERING.

    def test_a_measured_line_settled_just_short_of_the_limit_is_at_the_limit(self):
        self.node._on_cmd(String(data="lower"))
        self.client.sent[-1][1].finish()
        for m in (2.0, 4.0, 5.8, 5.929, 5.929):
            self.measure(m)
            self.node.integrate(0.1)
        self.assertEqual(self.node.state, "AT_LIMIT")
        self.assertAlmostEqual(self.node.payout, 5.929)

    def test_a_measured_line_well_short_of_the_limit_is_still_lowering(self):
        self.node._on_cmd(String(data="lower"))
        self.client.sent[-1][1].finish()
        for m in (2.0, 4.0, 5.5):
            self.measure(m)
            self.node.integrate(0.1)
        self.assertEqual(self.node.state, "LOWERING")

    def test_a_line_that_will_not_come_in_is_a_fault_not_stowed(self):
        self.node._on_cmd(String(data="stow"))
        for _ in range(200):            # 20 s, never retracts
            self.measure(2.6)
            self.node.integrate(0.1)
        self.assertEqual(self.node.state, "FAULT")
        self.assertIn("line not retracted: measured 2.60 m", self.node.fault)
