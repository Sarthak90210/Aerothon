#!/usr/bin/env python3
"""Unit test suite for GCS Aggregator telemetry snapshot and command dispatch."""

import sys
import unittest
import json
from unittest.mock import MagicMock

# Substitute mavros_msgs ONLY when it is genuinely unavailable. See the same
# note in sim/test_behavior_tree.py: the previous `not in sys.modules` guard
# poisoned sys.modules for every subsequently collected test file.
try:
    import mavros_msgs.msg  # noqa: F401
    import mavros_msgs.srv  # noqa: F401
except ImportError:
    m_msgs = MagicMock()
    sys.modules['mavros_msgs'] = m_msgs
    sys.modules['mavros_msgs.msg'] = m_msgs
    sys.modules['mavros_msgs.srv'] = m_msgs

from unittest.mock import patch, MagicMock

class TestGCSAggregator(unittest.TestCase):
    def setUp(self):
        with patch('rclpy.node.Node.__init__', return_value=None), \
             patch('rclpy.node.Node.create_subscription'), \
             patch('rclpy.node.Node.create_publisher'), \
             patch('rclpy.node.Node.create_client'), \
             patch('rclpy.node.Node.create_timer'), \
             patch('rclpy.node.Node.declare_parameter'), \
             patch('rclpy.node.Node.get_parameter', return_value=MagicMock(value="test-token")), \
             patch('rclpy.node.Node.get_logger'):
            from gcs_aggregator.aggregator import Aggregator, _euler_deg
            global _euler_deg_fn
            _euler_deg_fn = _euler_deg
            self.node = Aggregator()
            self.node.cli_arm = MagicMock()
            self.node.cli_mode = MagicMock()
            self.node.cli_takeoff = MagicMock()
            self.node.cli_land = MagicMock()
            self.node.pub_winch = MagicMock()
            self.node.pub_abort = MagicMock()
            self.node.pub_target = MagicMock()
            self.node.pub_start = MagicMock()
            self.node.state["safety"]["ready"] = True

    def test_euler_deg_conversion(self):
        """Test quaternion to euler degrees conversion."""
        q = MagicMock(x=0.0, y=0.0, z=0.0, w=1.0)
        roll, pitch, yaw = _euler_deg_fn(q)
        self.assertAlmostEqual(roll, 0.0, places=2)
        self.assertAlmostEqual(pitch, 0.0, places=2)
        self.assertAlmostEqual(yaw, 0.0, places=2)

    def test_command_dispatch_takeoff(self):
        """Test takeoff command triggers cli_takeoff."""
        res, reason = self.node._dispatch("takeoff", {"alt": 6.0})
        self.assertEqual(res, "accepted")

    def test_command_dispatch_land(self):
        """Test land command triggers land service."""
        res, reason = self.node._dispatch("land", {})
        self.assertEqual(res, "accepted")

    def test_command_dispatch_winch(self):
        """Test winch command publishes action."""
        res, reason = self.node._dispatch("winch", {"action": "lower"})
        self.assertEqual(res, "accepted")

    def test_command_dispatch_invalid(self):
        """Test unknown command returns rejected."""
        res, reason = self.node._dispatch("unknown_fly_command", {})
        self.assertEqual(res, "rejected")
        self.assertEqual(reason, "unknown cmd")

    def test_battery_telemetry_safety_flag(self):
        """Test battery low voltage correctly updates safety state."""
        batt = MagicMock(voltage=12.5, percentage=0.10)
        self.node._on_batt(batt)
        self.assertFalse(self.node.state["safety"]["battery_ok"])

        batt_ok = MagicMock(voltage=15.5, percentage=0.85)
        self.node._on_batt(batt_ok)
        self.assertTrue(self.node.state["safety"]["battery_ok"])


if __name__ == '__main__':
    unittest.main()
