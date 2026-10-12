#!/usr/bin/env python3
"""Winch command adapter with estimated travel and release-request interlocks.

The drone commands lower, stop and stow. Travel is integrated from commanded
motor rate; no encoder or contact/attachment sensor is present. The Gazebo
backend sends commanded payout only. Simulator contact release is a separate
component, and this node has no simulator-truth subscription.

Hardware uses MAV_CMD_DO_WINCH. Repeated motion intents are idempotent;
stop sends rate-control zero, not another full-length movement.

/winch/status reports payout_estimate_m and payout_basis. Legacy payout_m
is the same estimate. ground, released and hook_open are unknown. The
release_requested field records command acceptance, never physical release.
Delivery confirmation belongs to the onboard camera/load observer.
"""

import json
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped, TwistStamped
from std_msgs.msg import Empty, Float64, String

try:
    from mavros_msgs.srv import CommandLong
    _HAVE_MAVROS = True
except ImportError:
    _HAVE_MAVROS = False

MAV_CMD_DO_WINCH = 42600
WINCH_RELAXED, WINCH_RELATIVE_LENGTH_CONTROL, WINCH_RATE_CONTROL = 0, 1, 2

VALID_COMMANDS = ("lower", "release", "stow", "stop")


class WinchNode(Node):
    def __init__(self, **kwargs):
        super().__init__("winch_ctrl", **kwargs)
        p = self.declare_parameter
        p("backend", "sim")                  # sim | gazebo | mavlink
        p("payout_rate_mps", 0.30)           # line speed
        p("max_payout_m", 6.0)               # spool capacity
        p("ground_clearance_m", 0.25)        # payload considered down within this
        p("min_release_alt_m", 1.0)
        p("max_release_alt_m", 8.0)
        p("hover_speed_max_mps", 0.35)
        p("hover_stable_samples", 5)
        p("publish_rate_hz", 5.0)
        p("stow_rate_mps", 0.45)
        # HOW THE PAYLOAD LEAVES THE HOOK.
        #   gravity  the team's mechanism: a motor lowers a gravity-assisted
        #            hook that lets go by itself once the payload rests on the
        #            ground and the line goes slack. "release" is bookkeeping;
        #            nothing is sent to open anything.
        #   command  an actuated release: "release" opens the hook.
        p("hook", "gravity")
        # Legacy release-request travel interlock, never touchdown evidence.
        p("gravity_slack_m", 0.10)

        self.backend = self.get_parameter("backend").value

        self.state = "IDLE"
        self.payout = 0.0
        self.released = False
        self.fault = ""
        self._alt = None
        self._speed = None
        self._stable = 0
        self._last_tick = self._now()

        self.create_subscription(String, "/winch/cmd", self._on_cmd, 10)
        self.create_subscription(PoseStamped, "/mavros/local_position/pose",
                                 self._on_pose, qos_profile_sensor_data)
        self.create_subscription(TwistStamped,
                                 "/mavros/local_position/velocity_local",
                                 self._on_vel, qos_profile_sensor_data)
        self.pub_status = self.create_publisher(String, "/winch/status", 10)

        self.cli_cmd = None
        if self.backend == "mavlink" and _HAVE_MAVROS:
            self.cli_cmd = self.create_client(CommandLong, "/mavros/cmd/command")
        self.pub_gz_payout = None
        self.hook_open = False       # no physical release sensor fitted
        if self.backend == "gazebo":
            self._enable_gazebo()

        self.create_timer(1.0 / float(self.get_parameter("publish_rate_hz").value),
                          self._tick)
        self.get_logger().info(f"winch_ctrl up; backend={self.backend}")

    def _enable_gazebo(self):
        """Publish commanded travel to the simulated winch joint."""
        self.backend = "gazebo"
        self.pub_gz_payout = self.create_publisher(Float64, "/winch/gz/payout", 10)

    # ------------------------------------------------------------------ #
    def _now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def _on_pose(self, m):
        self._alt = m.pose.position.z

    def _on_vel(self, m):
        v = m.twist.linear
        self._speed = math.hypot(v.x, v.y)
        if self._speed <= float(self.get_parameter("hover_speed_max_mps").value):
            self._stable += 1
        else:
            self._stable = 0

    # ------------------------------------------------------------------ #
    def _on_cmd(self, msg: String):
        cmd = msg.data.strip().lower()
        if cmd not in VALID_COMMANDS:
            self.get_logger().warning(
                f"ignoring unknown winch command '{msg.data}' "
                f"(expected one of {VALID_COMMANDS})")
            return

        if cmd == "stop":
            if self.state == "IDLE" or self.state == "RELEASED":
                return
            self._send_backend("stop")
            self.state = "IDLE" if not self.released else "RELEASED"
            return

        if cmd == "lower":
            if self.state in ("LOWERING", "AT_LIMIT"):
                return
            if self.released:
                self._set_fault("cannot lower: payload already released")
                return
            self.state = "LOWERING"
            self._send_backend("lower")

        elif cmd == "release":
            if self.released:
                # Re-commanding release on a delivered payload is a redundant
                # instruction, not a malfunction. Raising a FAULT here left the
                # GCS showing an error for the whole return leg after a
                # delivery that had actually succeeded.
                self.get_logger().info("release ignored: payload already delivered")
                return
            ok, blockers = self.release_ok()
            if not ok:
                # Refuse, loudly. A silent no-op here is how the mission
                # believed it had delivered when it had not.
                self._set_fault("release refused: " + "; ".join(blockers))
                return
            self.released = True
            self.state = "RELEASED"
            self._send_backend("release")
            self.get_logger().info(
                f"payload RELEASED at alt={self._alt:.2f} m, "
                f"payout={self.payout:.2f} m")

        elif cmd == "stow":
            if self.state == "STOWING":
                return
            self.state = "STOWING"
            self._send_backend("stow")

    def _set_fault(self, reason):
        self.fault = reason
        self.state = "FAULT"
        self.get_logger().error(f"winch fault: {reason}")

    def _send_backend(self, action):
        if self.backend == "gazebo":
            return
        if self.backend != "mavlink" or self.cli_cmd is None:
            return
        if not self.cli_cmd.service_is_ready():
            return
        req = CommandLong.Request()
        req.command = MAV_CMD_DO_WINCH
        req.param1 = 1.0                                   # instance
        if action == "lower":
            req.param2 = float(WINCH_RELATIVE_LENGTH_CONTROL)
            req.param3 = max(0.0, float(self.get_parameter("max_payout_m").value) - self.payout)
            req.param4 = float(self.get_parameter("payout_rate_mps").value)
        elif action == "stow":
            req.param2 = float(WINCH_RELATIVE_LENGTH_CONTROL)
            req.param3 = -float(self.payout)
            req.param4 = float(self.get_parameter("stow_rate_mps").value)
        elif action == "stop":
            req.param2 = float(WINCH_RATE_CONTROL)
            req.param4 = 0.0
        else:
            req.param2 = float(WINCH_RELAXED)
        self.cli_cmd.call_async(req)

    # ------------------------------------------------------------------ #
    def at_ground(self):
        """Legacy travel estimate for command interlocks, NOT contact evidence."""
        if self._alt is None:
            return False
        if self.get_parameter("hook").value == "gravity":
            return self.payout >= self._alt + float(
                self.get_parameter("gravity_slack_m").value)
        clear = float(self.get_parameter("ground_clearance_m").value)
        return self.payout >= (self._alt - clear)

    def at_limit(self):
        return self.payout >= float(self.get_parameter("max_payout_m").value)

    def release_ok(self):
        """Return (ok, blockers). Every precondition is reported, not just the
        first, so the operator sees the whole picture at once.

        A delivered payload reports `released`, not a fault: the live run left
        the GCS showing `fault: release refused: already released` for the
        whole return leg, which reads as a malfunction when the delivery had
        in fact succeeded. Phase 10 is about the panel not lying; this is the
        same principle applied at the source.
        """
        if self.released:
            return False, ["payload already delivered"]
        blockers = list(self.physical_blockers())
        if self.fault:
            blockers.append(f"fault: {self.fault}")
        return (not blockers), blockers

    def physical_blockers(self):
        """Unmet PHYSICAL preconditions, ignoring any latched fault text.

        Kept separate because the fault-clearing check needs to ask "are the
        conditions met now?" without the answer being contaminated by the very
        refusal it is trying to clear — asking release_ok() there made the
        fault permanently self-justifying.
        """
        blockers = []
        if not (self.at_ground() or self.at_limit()):
            blockers.append(
                f"payload not down (payout {self.payout:.2f} m, "
                f"alt {self._alt if self._alt is None else round(self._alt, 2)})")
        if self._alt is None:
            blockers.append("no altitude")
        else:
            lo = float(self.get_parameter("min_release_alt_m").value)
            hi = float(self.get_parameter("max_release_alt_m").value)
            if not (lo <= self._alt <= hi):
                blockers.append(
                    f"altitude {self._alt:.2f} m outside [{lo}, {hi}]")
        # A gravity hook has let go by itself once the payload is down, so
        # its "release" only records that: holding it for a still hover
        # held the whole drop in a gusty wind with the payload already on
        # the ground (worst conditions). An actuated hook drops what it
        # holds, and a swinging aircraft throws it off the pad.
        need = int(self.get_parameter("hover_stable_samples").value)
        if self._stable < need and self.get_parameter("hook").value != "gravity":
            blockers.append(f"hover not stable ({self._stable}/{need})")
        return blockers

    # ------------------------------------------------------------------ #
    def _tick(self):
        now = self._now()
        dt = max(0.0, now - self._last_tick)
        self._last_tick = now
        self.integrate(dt)
        if self.pub_gz_payout is not None:
            self.pub_gz_payout.publish(Float64(data=float(self.payout)))
        self.publish_status()

    def integrate(self, dt):
        """Advance the spool by dt seconds.

        Separated from _tick so the state machine can be driven deterministically
        by tests and by replay, instead of depending on how fast the caller
        happens to loop.
        """
        # A refusal is a transient condition, not a latched failure: once the
        # payload is down and the aircraft is stable, the earlier "not down"
        # refusal must stop being reported.
        if self.fault.startswith("release refused") and not self.released:
            if not self.physical_blockers():
                self.fault = ""
                if self.state == "FAULT":
                    self.state = "AT_GROUND" if self.at_ground() else "IDLE"

        if self.state == "LOWERING":
            self.payout = min(
                float(self.get_parameter("max_payout_m").value),
                self.payout + float(self.get_parameter("payout_rate_mps").value) * dt)
            if self.at_limit():
                self.state = "AT_LIMIT"
        elif self.state == "STOWING":
            self.payout = max(
                0.0,
                self.payout - float(self.get_parameter("stow_rate_mps").value) * dt)
            if self.payout <= 1e-3:
                self.payout = 0.0
                self.state = "RELEASED" if self.released else "IDLE"

    def publish_status(self):
        ok, blockers = self.release_ok()
        payload = {
            "state": self.state,
            "payout_m": round(self.payout, 3),
            "at_limit": self.at_limit(),
            "ground": None,  # no contact sensor; travel cannot establish touchdown
            "payout_estimate_m": round(self.payout, 3),
            "payout_basis": "integrated commanded motor rate; no encoder",
            "released": None,
            "release_requested": self.released,
            "hook": self.get_parameter("hook").value,
            "hook_open": None,
            "fault": self.fault,
            "release_ok": ok,
            "blockers": blockers,
        }
        self.pub_status.publish(String(data=json.dumps(payload)))


def main():
    rclpy.init()
    node = WinchNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
