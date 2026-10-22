#!/usr/bin/env python3
"""Winch command adapter with estimated travel and release-request interlocks.

The drone commands lower, stop and stow. Travel is integrated from commanded
motor rate; no encoder or contact/attachment sensor is present. The Gazebo
backend sends commanded payout only. Simulator contact release is a separate
component, and this node has no simulator-truth subscription.

Hardware uses MAV_CMD_DO_WINCH, or with backend:=gpio the Pi drives the
BTS7960 directly and MEASURES travel from the N20 quadrature encoder
(gpio_winch.py); payout is then measured line movement, not an estimate.
Repeated motion intents are idempotent; stop sends rate-control zero, not
another full-length movement.

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
from std_msgs.msg import Float64, String

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
        p("backend", "sim")                  # sim | gazebo | mavlink | gpio
        p("payout_rate_mps", 0.30)           # line speed
        p("max_payout_m", 6.0)               # spool capacity
        p("ground_clearance_m", 0.25)        # payload considered down within this
        p("min_release_alt_m", 1.0)
        p("max_release_alt_m", 8.0)
        p("hover_speed_max_mps", 0.35)
        p("hover_stable_samples", 5)
        p("publish_rate_hz", 5.0)
        p("stow_rate_mps", 0.45)
        # backend:=mavlink -- the expected FC WINCH_RATE_MAX, at which
        # ArduPilot's relative-length control actually reels (it ignores the
        # requested rate). The estimate uses the value READ BACK from the FC;
        # lowering is refused until it has been read, and a mismatch is logged.
        p("fc_rate_max_mps", 0.30)
        # With a measured line (sim joint feedback): a stow that leaves more
        # than stow_window_m out is re-sent after this long without progress,
        # at most stow_retries times, then faults instead of reporting stowed.
        p("stow_stall_s", 2.0)
        p("stow_retries", 3)
        # HOW THE PAYLOAD LEAVES THE HOOK.
        #   gravity  the team's mechanism: a motor lowers a gravity-assisted
        #            hook that lets go by itself once the payload rests on the
        #            ground and the line goes slack. "release" is bookkeeping;
        #            nothing is sent to open anything.
        #   command  an actuated release: "release" opens the hook.
        p("hook", "gravity")
        p("external_joint_feedback", False)
        # Legacy release-request travel interlock, never touchdown evidence.
        p("gravity_slack_m", 0.10)
        # backend:=gpio -- BCM pins from hardware_wiring.yaml; the encoder
        # resolution, spool radius and lowering direction are MEASURED values
        # (0 = not measured, and the backend then refuses to start).
        p("gpio_chip", 0)
        p("gpio_rpwm", 18)
        p("gpio_lpwm", 19)
        p("gpio_r_en", 22)
        p("gpio_l_en", 23)
        p("gpio_encoder_a", 17)
        p("gpio_encoder_b", 27)
        p("pwm_hz", 1000.0)
        p("drive_duty_pct", 60.0)
        p("encoder_counts_per_output_rev", 0.0)
        p("spool_radius_m", 0.0)
        p("encoder_lower_sign", 1)
        p("stall_timeout_s", 0.6)
        p("stow_window_m", 0.15)

        self.backend = self.get_parameter("backend").value
        self.measured_payout = None
        self._measurement_t = None
        if self.get_parameter("external_joint_feedback").value is True:
            from sensor_msgs.msg import JointState
            self.create_subscription(JointState, '/joint_states', self._on_measured_payout, qos_profile_sensor_data)

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
        self.cli_param = None
        self.fc_winch = None         # (WINCH_TYPE, WINCH_RATE_MAX) read from the FC
        self._param_future = None
        self._param_t = None
        self._stow_retries = 0
        self._stow_progress = None   # (accumulated s, measured m) at last progress
        self._stow_clock = 0.0
        if self.backend == "mavlink" and _HAVE_MAVROS:
            self.cli_cmd = self.create_client(CommandLong, "/mavros/cmd/command")
            from rcl_interfaces.srv import GetParameters
            self.cli_param = self.create_client(GetParameters, "/mavros/param/get_parameters")
        self.pub_gz_payout = None
        self.hook_open = False       # no physical release sensor fitted
        if self.backend == "gazebo":
            self._enable_gazebo()
        self.gpio = None
        if self.backend == "gpio":
            self._enable_gpio()

        self.create_timer(1.0 / float(self.get_parameter("publish_rate_hz").value),
                          self._tick)
        self.get_logger().info(f"winch_ctrl up; backend={self.backend}")

    def _enable_gazebo(self):
        """Publish commanded travel to the simulated winch joint."""
        self.backend = "gazebo"
        self.pub_gz_payout = self.create_publisher(Float64, "/winch/gz/payout", 10)

    def _enable_gpio(self, driver=None, clock=None):
        """Start the measured GPIO winch, or fault closed with the reason."""
        from winch_ctrl.gpio_winch import EncoderWinch, LgpioDriver
        g = lambda name: self.get_parameter(name).value
        try:
            if driver is None:
                driver = LgpioDriver(g("gpio_chip"), g("gpio_rpwm"), g("gpio_lpwm"),
                                     g("gpio_r_en"), g("gpio_l_en"),
                                     g("gpio_encoder_a"), g("gpio_encoder_b"),
                                     g("pwm_hz"))
            self.gpio = EncoderWinch(
                driver, g("encoder_counts_per_output_rev"), g("spool_radius_m"),
                lower_sign=g("encoder_lower_sign"), drive_duty_pct=g("drive_duty_pct"),
                stall_timeout_s=g("stall_timeout_s"), stow_window_m=g("stow_window_m"),
                **({"clock": clock} if clock else {}))
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            self.gpio = None
            self._set_fault(f"gpio winch unavailable: {error}")

    def destroy_node(self):
        if getattr(self, "gpio", None) is not None:
            self.gpio.close()
        super().destroy_node()

    # ------------------------------------------------------------------ #
    def _now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def _on_pose(self, m):
        self._alt = m.pose.position.z

    def _on_measured_payout(self, msg):
        if 'winch_payout' not in msg.name:
            return
        index = list(msg.name).index('winch_payout')
        if index < len(msg.position) and math.isfinite(msg.position[index]) and msg.position[index] >= 0:
            self.measured_payout = float(msg.position[index])
            self._measurement_t = self._now()

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

        # A replacement motion/stop intent supersedes a release refusal. On
        # the bench its altitude interlock can never become true, so retaining
        # that refusal made safe stow fail and kept flight readiness blocked.
        # Backend/encoder failures remain latched and visible.
        if cmd in ("lower", "stow", "stop") and self.fault.startswith("release refused:"):
            self.fault = ""

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
            if self.backend == "mavlink":
                # Without the FC's own reel rate the payout estimate is a guess,
                # and a stow by that estimate left line hanging below the aircraft.
                if self.fc_winch is None:
                    self._set_fault("winch lower refused: FC WINCH_TYPE/WINCH_RATE_MAX not read back")
                    return
                if self.fc_winch[0] <= 0 or self.fc_winch[1] <= 0:
                    self._set_fault(f"winch lower refused: FC winch disabled (WINCH_TYPE {self.fc_winch[0]}, "
                                    f"WINCH_RATE_MAX {self.fc_winch[1]:g})")
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
                if self.fault and not self.fault.startswith("release refused:"):
                    # Do not relabel a hardware fault as a transient refusal:
                    # integrate() is allowed to clear only the latter.
                    self.get_logger().warning("release refused: " + "; ".join(blockers))
                    return
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
            self._stow_retries = 0
            self._stow_progress = None
            self._send_backend("stow")

    def _set_fault(self, reason):
        self.fault = reason
        self.state = "FAULT"
        self.get_logger().error(f"winch fault: {reason}")

    def _send_backend(self, action):
        if self.backend == "gpio":
            if self.gpio is None:
                if action != "stop":
                    self._set_fault(self.fault or "gpio winch unavailable")
                return
            if action in ("lower", "stow", "stop"):
                if not self.gpio.command(action):
                    self._set_fault(self.gpio.fault)
            # A gravity hook has no release actuator; "release" is bookkeeping.
            return
        if self.backend == "gazebo":
            return
        if self.backend != "mavlink" or self.cli_cmd is None:
            return
        if not self.cli_cmd.service_is_ready():
            # The node used to enter LOWERING anyway and grow a payout
            # estimate while nothing moved.
            if action in ("lower", "stow"):
                self._set_fault(f"winch {action} not sent: MAVROS command service unavailable")
            return
        self._mav_gen = getattr(self, "_mav_gen", 0) + 1
        self._mav_accepted = False
        gen = self._mav_gen
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
        future = self.cli_cmd.call_async(req)
        if future is not None and hasattr(future, "add_done_callback"):
            future.add_done_callback(
                lambda f, action=action, gen=gen: self._on_mav_reply(f, action, gen))

    def _on_mav_reply(self, future, action, gen):
        if gen != getattr(self, "_mav_gen", 0):
            return              # superseded by a later command
        try:
            reply = future.result()
        except Exception as exc:  # noqa: BLE001
            reply, why = None, str(exc)
        else:
            why = f"result {getattr(reply, 'result', None)}"
        if reply is not None and reply.success and int(reply.result) == 0:
            self._mav_accepted = True
            return
        if action in ("lower", "stow"):
            self._set_fault(f"flight controller refused DO_WINCH {action} ({why})")
        else:
            self.get_logger().warning(f"DO_WINCH {action} not accepted ({why})")

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
        self._request_fc_winch(now)
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

        if self.backend == "gpio":
            self._integrate_measured()
            return
        lower_rate = float(self.get_parameter("payout_rate_mps").value)
        stow_rate = float(self.get_parameter("stow_rate_mps").value)
        measured = self._measured()
        if measured is not None:
            self._integrate_line(measured, dt)
            return
        if self.backend == "mavlink":
            # ArduPilot's length control ignores DO_WINCH's rate and reels at
            # WINCH_RATE_MAX, both ways; and nothing moves before the FC accepts.
            if not getattr(self, "_mav_accepted", False):
                return
            lower_rate = stow_rate = self.fc_rate_max()
        if self.state == "LOWERING":
            self.payout = min(
                float(self.get_parameter("max_payout_m").value),
                self.payout + lower_rate * dt)
            if self.at_limit():
                self.state = "AT_LIMIT"
        elif self.state == "STOWING":
            self.payout = max(
                0.0,
                self.payout - stow_rate * dt)
            if self.payout <= 1e-3:
                self.payout = 0.0
                self.state = "RELEASED" if self.released else "IDLE"

    def fc_rate_max(self):
        """The FC's reel rate: read back when known, else the configured one."""
        if self.fc_winch is not None and self.fc_winch[1] > 0:
            return float(self.fc_winch[1])
        return float(self.get_parameter("fc_rate_max_mps").value)

    def _request_fc_winch(self, now):
        """Read WINCH_TYPE and WINCH_RATE_MAX from the FC (MAVROS parameters),
        then again every 10 s so a changed parameter is noticed."""
        if self.cli_param is None or self._param_future is not None:
            return
        if self._param_t is not None and now - self._param_t < (10.0 if self.fc_winch else 2.0):
            return
        if not self.cli_param.service_is_ready():
            return
        from rcl_interfaces.srv import GetParameters
        self._param_t = now
        self._param_future = self.cli_param.call_async(
            GetParameters.Request(names=["WINCH_TYPE", "WINCH_RATE_MAX"]))
        if self._param_future is not None and hasattr(self._param_future, "add_done_callback"):
            self._param_future.add_done_callback(self._on_fc_params_reply)

    def _on_fc_params_reply(self, future):
        self._param_future = None
        try:
            values = future.result().values
        except Exception:  # noqa: BLE001 - try again on the next period
            return
        self.on_fc_winch_params(values)

    def on_fc_winch_params(self, values):
        """rcl ParameterValues for (WINCH_TYPE, WINCH_RATE_MAX); type 0 = unset."""
        def number(v):
            return {2: v.integer_value, 3: v.double_value}.get(v.type)
        if len(values) != 2 or None in (number(values[0]), number(values[1])):
            return
        winch = (int(number(values[0])), float(number(values[1])))
        expected = float(self.get_parameter("fc_rate_max_mps").value)
        if winch != self.fc_winch and abs(winch[1] - expected) > 0.005:
            self.get_logger().warning(
                f"FC WINCH_RATE_MAX {winch[1]:g} m/s differs from fc_rate_max_mps "
                f"{expected:g}; estimating with the FC's value")
        self.fc_winch = winch

    def _measured(self, max_age=0.5):
        """A fresh measured line length (simulation joint), or None."""
        if self.gpio is not None or self.measured_payout is None or self._measurement_t is None:
            return None
        return self.measured_payout if self._now() - self._measurement_t <= max_age else None

    def _integrate_line(self, measured, dt):
        """The measured line drives the state machine: lowered, at the limit,
        or stowed only once the line is MEASURED in."""
        self.payout = measured
        if self.state == "LOWERING" and self.at_limit():
            self.state = "AT_LIMIT"
        if self.state != "STOWING":
            return
        window = float(self.get_parameter("stow_window_m").value)
        if measured <= window:
            self.payout = 0.0
            self.state = "RELEASED" if self.released else "IDLE"
            return
        # Still out: re-send the stow by the MEASURED length when it stalls.
        self._stow_clock += dt
        if self._stow_progress is None or measured < self._stow_progress[1] - 0.02:
            self._stow_progress = (self._stow_clock, measured)
            return
        if self._stow_clock - self._stow_progress[0] < float(self.get_parameter("stow_stall_s").value):
            return
        if self._stow_retries >= int(self.get_parameter("stow_retries").value):
            self._set_fault(f"line not retracted: measured {measured:.2f} m out after "
                            f"{self._stow_retries} further stow command(s)")
            return
        self._stow_retries += 1
        self._stow_progress = (self._stow_clock, measured)
        self.get_logger().warning(
            f"stow stalled with {measured:.2f} m measured out; re-sending stow "
            f"({self._stow_retries})")
        self._send_backend("stow")

    def _integrate_measured(self):
        """Measured encoder travel drives the same state machine."""
        if self.gpio is None:
            return
        event = self.gpio.update()
        self.payout = max(0.0, self.gpio.payout_m())
        self.measured_payout = self.payout
        self._measurement_t = self._now()
        if event == "fault":
            self._set_fault(self.gpio.fault)
            return
        if self.state == "LOWERING" and self.at_limit():
            self.gpio.stop()
            self.state = "AT_LIMIT"
        elif self.state == "STOWING" and (event == "stowed" or self.payout <= 1e-3):
            self.gpio.stop()
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
            "measured_payout_m": self.measured_payout,
            "measurement_age_s": None if self._measurement_t is None else max(0.0, self._now()-self._measurement_t),
            "payout_basis": ("measured N20 encoder travel" if self.gpio is not None
                             else "measured winch joint" if self._measured() is not None
                             else "integrated commanded motor rate; no encoder"),
            "fc_winch_type": None if self.fc_winch is None else self.fc_winch[0],
            "fc_rate_max_mps": None if self.fc_winch is None else self.fc_winch[1],
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
