#!/usr/bin/env python3
"""MAVROS commander — thin wrapper the behaviour tree calls into.

Holds the MAVROS clients/pubs/subs and a 10 Hz setpoint streamer so the
py_trees leaves stay simple (they poll state + issue intents; this object
does the ROS work). ArduPilot GUIDED flow: set GUIDED -> arm -> takeoff ->
stream position setpoints; hand the corridor to the avoidance node.

Phase 0 fail-closed rails live here:
  * setpoints are never published while the aircraft is disarmed
  * external LAND / DISARM / mode changes raise a mission-reset request
  * excessive attitude is measured and exposed to the abort guard
  * mission outcome is latched on /mission/result with an explicit reason
"""

import json
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import (QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy,
                       qos_profile_sensor_data)
from geometry_msgs.msg import PoseStamped, Vector3
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, String
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, SetMode, CommandTOL


# Modes the aircraft may legitimately enter under our own command. A change
# into any other mode, or into one of these without us asking, is treated as
# an outside intervention (safety pilot, Mission Planner, failsafe).
_TERMINAL_MODES = ("LAND", "RTL")

# How long after we issue a mode command we still consider that mode "ours".
_COMMAND_OWNERSHIP_S = 5.0


def _latched_qos(depth: int = 1) -> QoSProfile:
    """Transient-local QoS so a late-joining GCS still sees the last result."""
    return QoSProfile(
        depth=depth,
        history=QoSHistoryPolicy.KEEP_LAST,
        durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
    )


class Mav:
    def __init__(self, node: Node):
        self.node = node
        self.state = State()
        self.battery = BatteryState()
        self.pose = PoseStamped()
        self.qr_decoded = ""
        self.qr_matched = False
        self.qr_offset = Vector3()
        self.banner = Vector3()
        self.abort_requested = False
        self.abort_reason = ""
        # Once an abort fires it must STAY fired. The guard condition is
        # level-triggered (attitude recovers, battery sag recovers, the FCU
        # reconnects), so without a latch the mission silently resumed mid-air
        # after an abort had already commanded RTL. Cleared only by an explicit
        # new START or a mission reset.
        self.abort_latched = False
        self.mission_started = False

        # Default matches the official Iris SITL 3S battery. Override this ROS
        # parameter for a real airframe's battery chemistry / cell count.
        self.critical_battery_voltage = node.declare_parameter(
            'critical_battery_voltage', 10.5).value
        # Beyond this roll/pitch the aircraft is not flying the mission any
        # more, it is falling into something. The last recorded live run sat at
        # 54 deg against a corridor wall and nothing in the stack objected.
        self.attitude_limit_deg = node.declare_parameter(
            'attitude_limit_deg', 45.0).value
        # Consecutive pose samples beyond the limit before the guard trips, so
        # a single noisy quaternion cannot abort a healthy flight.
        self.attitude_limit_samples = node.declare_parameter(
            'attitude_limit_samples', 5).value

        self._sp = None            # streamed PoseStamped target (local ENU)

        # ---- fail-closed bookkeeping ---- #
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self._attitude_violations = 0
        self.setpoints_suppressed = 0      # counts gated publishes (testable)
        self.setpoint_block_reason = ""
        self._reset_requested = False
        self._reset_reason = ""
        self._expect_disarm = False        # set by the Land leaf
        self._commanded_modes = {}         # mode -> monotonic timestamp
        self._result = None                # latched (state, reason)

        qos = 10
        node.create_subscription(State, '/mavros/state', self._on_state, qos)
        node.create_subscription(BatteryState, '/mavros/battery', self._on_battery,
                                 qos_profile_sensor_data)
        node.create_subscription(PoseStamped, '/mavros/local_position/pose',
                                 self._on_pose, qos_profile_sensor_data)
        node.create_subscription(String, '/percep/qr/decoded', self._on_qr, qos)
        node.create_subscription(Bool, '/percep/qr/matched', self._on_match, qos)
        node.create_subscription(Vector3, '/percep/qr/target_offset', self._on_off, qos)
        node.create_subscription(Vector3, '/percep/banner', self._on_banner, qos)
        node.create_subscription(Bool, '/mission/abort', self._on_abort, qos)
        node.create_subscription(Bool, '/mission/start', self._on_start, qos)

        self.pub_sp = node.create_publisher(PoseStamped, '/mavros/setpoint_position/local', qos)
        self.pub_enable = node.create_publisher(Bool, '/avoidance/enable', qos)
        self.pub_target = node.create_publisher(String, '/mission/target', qos)
        self.pub_winch = node.create_publisher(String, '/winch/cmd', qos)
        self.pub_result = node.create_publisher(String, '/mission/result', _latched_qos())

        self.cli_arm = node.create_client(CommandBool, '/mavros/cmd/arming')
        self.cli_mode = node.create_client(SetMode, '/mavros/set_mode')
        self.cli_takeoff = node.create_client(CommandTOL, '/mavros/cmd/takeoff')
        self.cli_land = node.create_client(CommandTOL, '/mavros/cmd/land')

        node.create_timer(0.1, self._stream)   # 10 Hz setpoint stream

    # ------------------------------------------------------------------ #
    # callbacks
    # ------------------------------------------------------------------ #
    def _on_battery(self, m): self.battery = m
    def _on_qr(self, m): self.qr_decoded = m.data
    def _on_match(self, m): self.qr_matched = m.data
    def _on_off(self, m): self.qr_offset = m
    def _on_banner(self, m): self.banner = m

    def _on_abort(self, m):
        self.abort_requested = m.data

    def _on_start(self, m):
        self.mission_started = m.data
        if m.data:
            self._result = None
            # A previous run's Land leaf leaves _expect_disarm set. Carrying it
            # into a new mission would make the watchdog swallow a genuine
            # external disarm, so every start begins with a clean slate.
            self._expect_disarm = False
            self.abort_reason = ""
            self.abort_latched = False
            self._attitude_violations = 0
            self.node.get_logger().info("Mission 2 start received from GCS")

    def _on_pose(self, m):
        self.pose = m
        self.roll_deg, self.pitch_deg = self._rp_deg(m.pose.orientation)
        worst = max(abs(self.roll_deg), abs(self.pitch_deg))
        if worst > self.attitude_limit_deg:
            self._attitude_violations += 1
        else:
            self._attitude_violations = 0

    def _on_state(self, m):
        prev = self.state
        self.state = m
        # Only an active mission can be interrupted; a disarmed idle aircraft
        # changing mode on the bench is not an event.
        if not self.mission_started:
            return

        if prev.armed and not m.armed:
            if self._expect_disarm:
                self.node.get_logger().info("Disarm observed during commanded landing")
            else:
                self._request_reset("external disarm")

        if m.mode != prev.mode and m.mode in _TERMINAL_MODES:
            if not self._mode_was_ours(m.mode):
                self._request_reset(f"external mode change to {m.mode}")

    # ------------------------------------------------------------------ #
    # attitude
    # ------------------------------------------------------------------ #
    @staticmethod
    def _rp_deg(q):
        """Roll and pitch in degrees from a geometry_msgs Quaternion."""
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        sinp = max(-1.0, min(1.0, sinp))
        pitch = math.asin(sinp)
        return math.degrees(roll), math.degrees(pitch)

    def attitude_excessive(self):
        """True once the aircraft has held an unflyable attitude for N samples."""
        return self._attitude_violations >= self.attitude_limit_samples

    # ------------------------------------------------------------------ #
    # mission reset (external intervention)
    # ------------------------------------------------------------------ #
    def _request_reset(self, reason):
        if self._reset_requested:
            return
        self._reset_requested = True
        self._reset_reason = reason
        self.node.get_logger().warning(f"Mission reset requested: {reason}")

    def reset_pending(self):
        return self._reset_requested

    def consume_reset(self):
        """Returns the pending reset reason (or None) and clears mission state."""
        if not self._reset_requested:
            return None
        reason = self._reset_reason
        self._reset_requested = False
        self._reset_reason = ""
        self.mission_started = False
        self.abort_requested = False
        self.abort_latched = False
        self._expect_disarm = False
        self._attitude_violations = 0
        self._sp = None
        return reason

    def expect_disarm(self, value=True):
        self._expect_disarm = bool(value)

    # ------------------------------------------------------------------ #
    # outcome reporting
    # ------------------------------------------------------------------ #
    def publish_result(self, state, reason=""):
        """Latch a terminal mission outcome. First writer per run wins."""
        if self._result is not None:
            return
        self._result = (state, reason)
        payload = json.dumps({
            "state": state,
            "reason": reason,
            "t": self.node.get_clock().now().nanoseconds / 1e9,
        })
        self.pub_result.publish(String(data=payload))
        self.node.get_logger().info(f"Mission result: {state} ({reason})")

    @property
    def result(self):
        return self._result

    # ------------------------------------------------------------------ #
    # setpoint streaming (gated)
    # ------------------------------------------------------------------ #
    def _stream(self):
        if self._sp is None:
            return
        # Fail-closed rail: a disarmed aircraft must never be streamed
        # position setpoints. Previously the mission kept publishing after an
        # external disarm, so the tree looked alive while nothing was flying.
        if not self.state.armed:
            self.setpoints_suppressed += 1
            self.setpoint_block_reason = "disarmed"
            return
        self.setpoint_block_reason = ""
        self._sp.header.stamp = self.node.get_clock().now().to_msg()
        self._sp.header.frame_id = 'map'
        self.pub_sp.publish(self._sp)

    # ------------------------------------------------------------------ #
    # intents (non-blocking)
    # ------------------------------------------------------------------ #
    def connected(self):
        return self.state.connected

    def battery_critical(self, min_volt=None, min_pct=0.15):
        """Returns True if battery is below safe critical threshold."""
        if min_volt is None:
            min_volt = self.critical_battery_voltage
        if self.battery.voltage > 0.0 and self.battery.voltage < min_volt:
            return True
        if self.battery.percentage > 0.0 and self.battery.percentage < min_pct:
            return True
        return False

    def _note_mode_command(self, mode):
        self._commanded_modes[mode] = self.node.get_clock().now().nanoseconds / 1e9

    def _mode_was_ours(self, mode):
        t = self._commanded_modes.get(mode)
        if t is None:
            return False
        now = self.node.get_clock().now().nanoseconds / 1e9
        return (now - t) <= _COMMAND_OWNERSHIP_S

    def set_mode(self, mode='GUIDED'):
        self._note_mode_command(mode)
        if self.cli_mode.service_is_ready():
            req = SetMode.Request(); req.custom_mode = mode
            self.cli_mode.call_async(req)

    def arm(self, value=True):
        if self.cli_arm.service_is_ready():
            req = CommandBool.Request(); req.value = value
            self.cli_arm.call_async(req)

    def takeoff(self, alt):
        if self.cli_takeoff.service_is_ready():
            req = CommandTOL.Request(); req.altitude = float(alt)
            self.cli_takeoff.call_async(req)

    def land(self):
        self._note_mode_command("LAND")
        if self.cli_land.service_is_ready():
            req = CommandTOL.Request()
            self.cli_land.call_async(req)
        else:
            self.set_mode("LAND")

    def goto(self, x, y, z, yaw=0.0):
        """Stream position setpoint with heading orientation (yaw in radians)."""
        sp = PoseStamped()
        sp.pose.position.x = float(x)
        sp.pose.position.y = float(y)
        sp.pose.position.z = float(z)
        half_yaw = float(yaw) / 2.0
        sp.pose.orientation.z = math.sin(half_yaw)
        sp.pose.orientation.w = math.cos(half_yaw)
        self._sp = sp

    def pos(self):
        p = self.pose.pose.position
        return (p.x, p.y, p.z)

    def reached(self, x, y, z, tol=0.6):
        px, py, pz = self.pos()
        return math.dist((px, py, pz), (x, y, z)) < tol

    def alt(self):
        return self.pose.pose.position.z

    def enable_avoidance(self, on):
        self.pub_enable.publish(Bool(data=bool(on)))
        if on:
            self._sp = None    # stop position streaming; avoidance drives velocity

    def set_target(self, s):
        self.pub_target.publish(String(data=s))

    def winch(self, cmd):
        self.pub_winch.publish(String(data=cmd))   # "lower" | "release" | "stow"
