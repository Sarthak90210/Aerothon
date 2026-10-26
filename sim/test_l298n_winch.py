#!/usr/bin/env python3
"""Pi L298N payload motor (winch_ctrl backend:=l298n) and an RC switch by hand.

The team bench-tested the motor through an L298N (ESP32, 24 Oct 2026):
ENA enables, IN1/IN2 set the direction. On the aircraft the Pi drives the
same three lines, and an RC switch drives it by hand -- high one way, low the
other, middle nothing -- except during an autonomous mission, when the switch
is ignored completely. The node's default is channel 5; the aircraft's venue
selects RC6, its three-position switch (channel 5 there has two positions).

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_l298n_winch.py -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "aerothon_payload", "winch_ctrl"))

import rclpy
from rclpy.parameter import Parameter
from std_msgs.msg import String

from winch_ctrl.l298n import FORWARD, REVERSE, STOP, L298NDriver
from winch_ctrl.winch_node import WinchNode


class FakeLgpio:
    """Records pin levels and PWM like lgpio would drive them."""

    def __init__(self):
        self.level, self.pwm, self.writes, self.freed, self.closed = {}, {}, [], [], False

    def gpiochip_open(self, chip):
        return 7

    def gpio_claim_output(self, h, pin, level):
        self.level[pin] = level

    def gpio_write(self, h, pin, level):
        self.level[pin] = level
        self.writes.append((pin, level))

    def tx_pwm(self, h, pin, hz, duty):
        self.pwm[pin] = (hz, duty)

    def gpio_free(self, h, pin):
        self.freed.append(pin)

    def gpiochip_close(self, h):
        self.closed = True


class DriverTests(unittest.TestCase):

    def setUp(self):
        self.lg = FakeLgpio()
        self.d = L298NDriver(0, 18, 23, 24, lg=self.lg)

    def test_forward_reverse_and_stop_match_the_bench_test(self):
        self.d.drive(FORWARD)
        self.assertEqual((self.lg.level[23], self.lg.level[24], self.lg.level[18]), (1, 0, 1))
        self.d.drive(REVERSE)
        self.assertEqual((self.lg.level[23], self.lg.level[24], self.lg.level[18]), (0, 1, 1))
        self.d.drive(STOP)
        self.assertEqual((self.lg.level[23], self.lg.level[24], self.lg.level[18]), (0, 0, 0))

    def test_direction_changes_only_with_the_bridge_disabled(self):
        self.d.drive(FORWARD)
        self.lg.writes.clear()
        self.d.drive(REVERSE)
        self.assertEqual(self.lg.writes[0], (18, 0), 'ENA off before IN1/IN2 change')
        self.assertEqual(self.lg.writes[-1], (18, 1))

    def test_fc_uart_pins_are_refused(self):
        for pins in ((4, 23, 24), (18, 14, 24), (18, 23, 15), (5, 6, 7)):
            with self.assertRaises(ValueError):
                L298NDriver(0, *pins, lg=FakeLgpio())

    def test_part_duty_uses_pwm_on_enable(self):
        lg = FakeLgpio()
        d = L298NDriver(0, 18, 23, 24, pwm_hz=1000, duty_pct=60, lg=lg)
        d.drive(FORWARD)
        self.assertEqual(lg.pwm[18], (1000.0, 60.0))
        d.drive(STOP)
        self.assertEqual(lg.pwm[18], (0, 0))

    def test_close_stops_and_releases(self):
        self.d.drive(FORWARD)
        self.d.close()
        self.assertEqual(self.lg.level[18], 0)
        self.assertEqual(sorted(self.lg.freed), [18, 23, 24])
        self.assertTrue(self.lg.closed)


class FakeRC:
    def __init__(self, ch5, ch6=1500):
        self.channels = [1500, 1500, 1000, 1500, ch5, ch6, 1500, 1500]


class NodeTests(unittest.TestCase):

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
        self.node = WinchNode(parameter_overrides=[
            Parameter("backend", Parameter.Type.STRING, "l298n"),
            Parameter("payout_rate_mps", Parameter.Type.DOUBLE, 0.30),
            Parameter("max_payout_m", Parameter.Type.DOUBLE, 1.0)])
        self.node.pub_status.publish = lambda *_: None
        self.lg = FakeLgpio()
        self.node.motor = L298NDriver(0, 18, 23, 24, lg=self.lg)
        self.node.fault, self.node.state = "", "IDLE"   # no lgpio on the test host

    def tearDown(self):
        self.node.destroy_node()

    def tick(self, dt=0.2, n=1):
        for _ in range(n):
            self.node.integrate(dt)
            self.node._sync_l298n(dt)

    def rc(self, us):
        self.node._on_rc(FakeRC(us))

    def mission(self, state):
        self.node._on_mission_state(String(data=state))

    def centre(self):
        """The operator puts channel 5 in the middle, which readies hand drive."""
        self.rc(1500)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)

    def test_lower_drives_the_lowering_direction_and_stops_at_the_limit(self):
        self.node._on_cmd(String(data="lower"))
        self.assertEqual(self.node.motor.direction, FORWARD)
        self.tick(0.5, 8)                              # 0.30 m/s past 1.0 m
        self.assertEqual(self.node.state, "AT_LIMIT")
        self.assertEqual(self.node.motor.direction, STOP)

    def test_stow_reverses_and_stops_when_the_estimate_is_home(self):
        self.node.payout = 0.4
        self.node._on_cmd(String(data="stow"))
        self.assertEqual(self.node.motor.direction, REVERSE)
        self.tick(0.5, 4)
        self.assertEqual(self.node.state, "IDLE")
        self.assertEqual(self.node.motor.direction, STOP)

    def test_lower_direction_can_be_flipped_after_the_bench_check(self):
        self.node.set_parameters([Parameter("l298n_lower_direction", Parameter.Type.INTEGER, -1)])
        self.node._on_cmd(String(data="lower"))
        self.assertEqual(self.node.motor.direction, REVERSE)

    def test_channel_5_high_and_low_spin_opposite_ways_middle_does_nothing(self):
        self.centre()
        self.rc(2000)
        self.tick()
        self.assertEqual(self.node.motor.direction, FORWARD)
        self.rc(1000)
        self.tick()
        self.assertEqual(self.node.motor.direction, REVERSE)
        self.rc(1500)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)

    def test_channel_5_is_ignored_completely_during_a_mission(self):
        self.mission("SEARCH_QR")
        self.rc(2000)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)
        self.node._on_cmd(String(data="lower"))
        self.rc(1000)
        self.tick()
        self.assertEqual(self.node.motor.direction, FORWARD, 'the mission lower is not overridden')

    def test_a_mission_starting_stops_a_hand_drive(self):
        self.centre()
        self.rc(2000)
        self.tick()
        self.assertEqual(self.node.motor.direction, FORWARD)
        self.mission("PREFLIGHT")
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)
        self.mission("COMPLETED")
        self.rc(2000)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP, 'a switch left high after the mission waits')
        self.centre()
        self.rc(2000)
        self.tick()
        self.assertEqual(self.node.motor.direction, FORWARD, 'hand drive returns after the mission')

    def test_a_lost_or_stale_radio_stops_the_hand_drive(self):
        self.centre()
        self.rc(2000)
        self.tick()
        self.node._rc = (self.node._rc[0], self.node._now() - 5.0)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)
        self.rc(2000)                                  # the radio returns with the switch high
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)
        self.centre()
        self.rc(0)                                     # failsafe / no signal
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)
        self.rc(1000)
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP, 'a failsafe value needs the middle again')

    def test_a_switch_left_at_either_end_never_starts_the_motor(self):
        # Aircraft, 25 Oct 2026: channel 5 at LOW when the runtime connected
        # at boot lowered the line unattended.
        for us in (1000, 2000):
            self.node.rc_ready = False
            self.rc(us)
            self.tick(0.5, 4)
            self.assertEqual(self.node.motor.direction, STOP, us)
            self.assertEqual(self.node.payout, 0.0)
            self.rc(3000 - us)                             # flipped straight to the other end
            self.tick()
            self.assertEqual(self.node.motor.direction, STOP, us)
        self.centre()
        self.rc(1000)
        self.tick()
        self.assertEqual(self.node.motor.direction, REVERSE)

    def test_on_channel_6_the_two_position_channel_5_does_nothing(self):
        # Aircraft, 25 Oct 2026: channel 5 is a two-position switch (1000/2000
        # only, never a stop); the operator moved hand drive to RC6, three-position.
        self.node.set_parameters([Parameter("rc_manual_channel", Parameter.Type.INTEGER, 6)])
        self.node._on_rc(FakeRC(1500, 1500))
        self.tick()
        for ch5 in (1000, 2000, 1000):
            self.node._on_rc(FakeRC(ch5, 1500))
            self.tick()
            self.assertEqual(self.node.motor.direction, STOP, ch5)
        self.node._on_rc(FakeRC(2000, 2000))
        self.tick()
        self.assertEqual(self.node.motor.direction, FORWARD)
        self.node._on_rc(FakeRC(2000, 1000))
        self.tick()
        self.assertEqual(self.node.motor.direction, REVERSE)
        self.node._on_rc(FakeRC(1000, 1500))
        self.tick()
        self.assertEqual(self.node.motor.direction, STOP)

    def test_hand_drive_keeps_the_payout_estimate(self):
        self.centre()
        self.rc(2000)
        self.tick(0.5, 2)
        self.assertAlmostEqual(self.node.payout, 0.30, places=6)
        self.rc(1000)
        self.tick(0.5, 4)
        self.assertEqual(self.node.payout, 0.0)


class ContractTests(unittest.TestCase):

    def test_profiles_accept_l298n_on_the_drone_only(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                        "src", "aerothon_runtime"))
        from aerothon_runtime.contracts import profile
        p = profile({"id": "vehicle", "transport": "serial", "device": "/dev/ttyAMA0",
                     "vehicle": "drone", "winch_backend": "l298n"})
        self.assertEqual(p["winch_backend"], "l298n")
        with self.assertRaises(ValueError):
            profile({"id": "sim", "transport": "tcp", "host": "127.0.0.1", "vehicle": "simulation",
                     "gateway": "http://127.0.0.1:8090", "winch_backend": "l298n"})

    def test_the_aircraft_drives_by_hand_on_the_three_position_rc6(self):
        import yaml
        config = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "src", "aerothon_mission", "mission_bringup", "config")
        venue = yaml.safe_load(open(os.path.join(config, "venue.yaml")))
        wiring = yaml.safe_load(open(os.path.join(config, "hardware_wiring.yaml")))
        self.assertEqual(venue["winch_ctrl"]["ros__parameters"]["rc_manual_channel"], 6)
        self.assertEqual(wiring["winch"]["l298n"]["rc_manual_channel"], 6)


if __name__ == "__main__":
    unittest.main()
