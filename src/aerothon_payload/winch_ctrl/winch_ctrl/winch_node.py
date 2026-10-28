#!/usr/bin/env python3
"""Winch command adapter with estimated travel and release-request interlocks.

The drone commands lower, stop and stow. Travel is integrated from commanded
motor rate; no encoder or contact/attachment sensor is present. The Gazebo
backend sends commanded payout only. Simulator contact release is a separate
component, and this node has no simulator-truth subscription.

Hardware uses MAV_CMD_DO_WINCH, or with backend:=gpio the Pi drives the
BTS7960 directly and MEASURES travel from the N20 quadrature encoder
(gpio_winch.py); payout is then measured line movement, not an estimate.
With backend:=l298n the Pi drives an L298N (l298n.py) with no encoder; payout
is the timed estimate. An RC switch (rc_manual_channel; 6, a three-position
switch, on the aircraft) then also drives it by hand (high one way, low the
other, middle stop) whenever no autonomous mission is running. A gap in the
channels shorter than rc_loss_s pauses it; a longer one needs the middle.

WINCH LIMITS (backend:=l298n). The GCS calibrates where the line stops: the
operator opens a calibration (/winch/calibration {"action": "begin"}), which
lifts the limits for the hand switch, winds the line up to where it should
stop and marks it ("set_min"), pays it out to where it should stop and marks
that with the line length measured there ("set_max", "length_m"). The mark
becomes the limit for hand drive, the mechanism tests and the mission's
lower, and the run time between the marks gives the line speed both ways.
It is saved to `limits_file` with the line position, so a restart keeps both.
Repeated motion intents are idempotent; stop sends rate-control zero, not
another full-length movement.

/winch/status reports payout_estimate_m and payout_basis. Legacy payout_m
is the same estimate. ground, released and hook_open are unknown. The
release_requested field records command acceptance, never physical release.
Delivery confirmation belongs to the onboard camera/load observer.
"""

import json
import math
import os
import time

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
try:
    from mavros_msgs.msg import RCIn
except ImportError:
    RCIn = None

# Mission states in which no autonomous flight is running (mission_tree
# IDLE_STATES plus a finished abort): the RC hand switch may drive the motor only then.
MISSION_IDLE_STATES = frozenset({"", "IDLE", "WAITING", "COMPLETED", "FAILED", "ABORTED"})

MAV_CMD_DO_WINCH = 42600
WINCH_RELAXED, WINCH_RELATIVE_LENGTH_CONTROL, WINCH_RATE_CONTROL = 0, 1, 2

VALID_COMMANDS = ("lower", "release", "stow", "stop")


class WinchNode(Node):
    def __init__(self, **kwargs):
        super().__init__("winch_ctrl", **kwargs)
        p = self.declare_parameter
        p("backend", "sim")                  # sim | gazebo | mavlink | gpio | l298n
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
        # A DO_WINCH MAVROS stopped waiting on (success false, result 0) is
        # taken as accepted if the measured line moves its way within this.
        p("unacked_motion_s", 3.0)
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
        # A measured line within this of max_payout_m is at the limit, as one
        # within stow_window_m of home is stowed: the FC's length control
        # settles short of the length it was sent (SITL: 5.929 of 6.0 m), and
        # a bench "lower" stayed LOWERING for ever (gcs_testing_20261025).
        p("limit_window_m", 0.15)
        # backend:=l298n -- the team's L298N (bench-tested 24 Oct 2026): ENA,
        # IN1, IN2 as BCM pins (not 4/5/14/15: FC UARTs). lower_direction 1
        # lowers on IN1 (the test's "forward"), -1 on IN2: check on the bench.
        p("l298n_ena", 18)
        p("l298n_in1", 23)
        p("l298n_in2", 24)
        p("l298n_duty_pct", 100.0)
        p("l298n_lower_direction", 1)
        # RC switch by hand (backend:=l298n; venue.yaml selects channel 6, a
        # three-position switch, on the aircraft): at or above rc_high_us spins
        # IN1 ("forward"), at or below rc_low_us IN2; the middle and a lost
        # or stale radio stop it. Ignored completely during a mission. After
        # startup, a mission or a lost radio the switch must be seen in the
        # middle first (aircraft, 25 Oct: a switch left at LOW lowered at boot).
        # Channels silent past rc_timeout_s pause the motor; only silence past
        # rc_loss_s is a lost radio that needs the middle again (aircraft,
        # 29 Oct: a gap in the 5 Hz channels stopped the motor with RC6
        # held, and it stayed stopped until the switch went back to the middle).
        p("rc_manual_channel", 5)
        p("rc_high_us", 1800)
        p("rc_low_us", 1200)
        p("rc_timeout_s", 0.5)
        p("rc_loss_s", 2.0)
        # Winch limits calibrated at the GCS (backend:=l298n); "" keeps none.
        p("limits_file", "")
        p("calibration_timeout_s", 600.0)    # an open calibration lifts the limits
        # The mission releases from no higher than the line less this
        # (mission_tree WinchDrop), and winch_ctrl from no lower than
        # min_release_alt_m: a shorter line cannot deliver.
        p("min_calibrated_payout_m", 1.5)

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
        self._unacked = None         # (action, node time, measured m): see _on_mav_reply
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
        self.motor = None
        self._rc = None              # (channels, receipt time) from /aerothon/rc/in
        self._mission_state = ""
        self.manual = 0              # RC hand drive in effect: 1, -1 or 0
        self.rc_ready = False        # hand switch seen in the middle since startup/mission/lost radio
        self.rc_reason = ""          # what hand drive is doing and why, logged on change
        self.limit = None            # calibrated {max_payout_m, line_speed_mps, stroke_s, saved_at}
        self.limit_source = "max_payout_m parameter (not calibrated)"
        self.cal_until = None        # an open calibration's end, node time
        self.cal_zeroed = False      # wound-up marked in this calibration
        self.cal_run_s = 0.0         # net lowering run time since that mark
        self.cal_reason = ""
        self._saved_payout = None
        if self.backend == "l298n":
            self._enable_l298n()
            if RCIn is not None:
                # rc_in_bridge: the FC's channels even with chancount 0 (ExpressLRS
                # in MAVLink mode), where /mavros/rc/in is empty.
                self.create_subscription(RCIn, "/aerothon/rc/in", self._on_rc, qos_profile_sensor_data)
            self.create_subscription(String, "/mission/state", self._on_mission_state, 10)
            self._load_limits()
        self.create_subscription(String, "/winch/calibration", self._on_calibration, 10)

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

    def _enable_l298n(self, driver=None):
        from winch_ctrl.l298n import L298NDriver
        g = lambda n: self.get_parameter(n).value  # noqa: E731
        try:
            self.motor = driver or L298NDriver(
                g("gpio_chip"), g("l298n_ena"), g("l298n_in1"), g("l298n_in2"),
                g("pwm_hz"), g("l298n_duty_pct"))
        except Exception as error:  # noqa: BLE001 - no lgpio, busy pins, bad wiring
            self.motor = None
            self._set_fault(f"l298n winch unavailable: {error}")

    def _on_rc(self, msg):
        self._rc = (list(msg.channels), self._now())

    def _on_mission_state(self, msg):
        self._mission_state = str(msg.data).split(":")[0].strip()

    def mission_active(self):
        return self._mission_state not in MISSION_IDLE_STATES

    def rc_manual_direction(self):
        """1 (IN1), -1 (IN2) or 0 from the RC hand switch. 0 during a mission, for
        a middle stick, for a missing or stale radio, and until the switch has
        been seen in the middle since startup, the last mission or the last
        lost radio: a switch left at either end never starts the motor. A
        brief gap in the channels only pauses it: the switch still held when
        they return drives on."""
        band = self._rc_band()
        if band is None:
            if self._rc_brief_gap():
                self._rc_note("paused: no channels for over rc_timeout_s")
            else:
                self.rc_ready = False
                self._rc_note("off: mission, no radio or failsafe; middle first")
            return 0
        if band == 0:
            self.rc_ready = True
            self._rc_note("stopped: switch in the middle")
        elif not self.rc_ready:
            self._rc_note("waiting: switch to the middle first")
        return band if self.rc_ready else 0

    def _rc_brief_gap(self):
        """True while the channels have been silent past rc_timeout_s but not
        yet rc_loss_s, the last value valid and no mission running."""
        if self.mission_active() or self._rc is None:
            return False
        channels, t = self._rc
        i = int(self.get_parameter("rc_manual_channel").value) - 1
        if not 0 <= i < len(channels) or int(channels[i]) < 900:
            return False
        return self._now() - t <= float(self.get_parameter("rc_loss_s").value)

    def _rc_note(self, reason):
        """Log what hand drive is doing, once per change."""
        if reason != self.rc_reason:
            self.rc_reason = reason
            self.get_logger().info(f"hand drive {reason}")

    def _rc_band(self):
        """1 high, -1 low, 0 middle; None for a mission, a missing, stale or
        failsafe radio, or no such channel."""
        if self.mission_active() or self._rc is None:
            return None
        channels, t = self._rc
        if self._now() - t > float(self.get_parameter("rc_timeout_s").value):
            return None
        i = int(self.get_parameter("rc_manual_channel").value) - 1
        if not 0 <= i < len(channels):
            return None
        us = int(channels[i])
        if us < 900:
            return None
        if us >= int(self.get_parameter("rc_high_us").value):
            return 1
        if us <= int(self.get_parameter("rc_low_us").value):
            return -1
        return 0

    def _sync_l298n(self, dt):
        """Drive the L298N for the winch state, else for the RC hand switch."""
        if self.motor is None:
            return
        lower = 1 if int(self.get_parameter("l298n_lower_direction").value) >= 0 else -1
        if self.calibrating() and (self.mission_active() or self._now() >= self.cal_until):
            self._end_calibration("a mission started" if self.mission_active()
                                  else "the calibration timed out")
        want = 0
        self.manual = 0
        if self.state == "LOWERING":
            want = lower
        elif self.state == "STOWING":
            want = -lower
        elif self.state != "FAULT":
            self.manual = self.rc_manual_direction()
            if self.manual:
                # Hand drive moves the line too: keep the estimate honest.
                step = self.line_speed() * dt
                if self.calibrating():
                    # Limits lifted: the operator is finding where they go.
                    self.cal_run_s += dt if self.manual == lower else -dt
                    self.payout += step if self.manual == lower else -step
                    self._rc_note("paying out (calibration)" if self.manual == lower
                                  else "winding in (calibration)")
                elif self.manual == lower:
                    if self.limit and self.payout >= self.max_payout():
                        self.manual = 0          # at the calibrated paid-out limit
                        self._rc_note("stopped: at the calibrated paid-out limit")
                    else:
                        self.payout = min(self.max_payout(), self.payout + step)
                        self._rc_note("paying out")
                elif self.limit and self.payout <= 0.0:
                    self.manual = 0              # at the calibrated wound-up limit
                    self._rc_note("stopped: at the calibrated wound-up limit")
                else:
                    self.payout = max(0.0, self.payout - step)
                    self._rc_note("winding in")
            want = self.manual
        if want != self.motor.direction:
            self.motor.drive(want)
            if want == 0:
                self._save_position()

    # ------------------------------------------------------------------ #
    # winch limits (backend:=l298n)
    # ------------------------------------------------------------------ #
    def max_payout(self):
        """The paid-out limit: calibrated at the GCS, else the parameter."""
        if self.limit:
            return float(self.limit["max_payout_m"])
        return float(self.get_parameter("max_payout_m").value)

    def line_speed(self):
        """Line speed both ways on the L298N: one motor at one duty. Timed
        between the calibration marks once there are some."""
        if self.limit:
            return float(self.limit["line_speed_mps"])
        return float(self.get_parameter("payout_rate_mps").value)

    def calibrating(self):
        return self.cal_until is not None

    def _limits_path(self):
        path = str(self.get_parameter("limits_file").value or "")
        return os.path.expanduser(path) if path else ""

    def _load_limits(self):
        path = self._limits_path()
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            limit = self._valid_limit(data["limit"])
            position = float(data.get("position_m", 0.0))
            if not math.isfinite(position) or not 0.0 <= position <= limit["max_payout_m"]:
                raise ValueError(f"saved position {position} m is outside the limits")
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.get_logger().warning(f"saved winch limits ignored: {error}")
            self.cal_reason = f"saved limits ignored: {error}"
            return
        self.limit, self.payout = limit, position
        self._saved_payout = position
        self.limit_source = f"saved calibration ({path})"

    def _valid_limit(self, limit):
        out = {k: float(limit[k]) for k in ("max_payout_m", "line_speed_mps", "stroke_s")}
        if not all(math.isfinite(v) and v > 0 for v in out.values()):
            raise ValueError("winch limits must be positive numbers")
        if out["max_payout_m"] < float(self.get_parameter("min_calibrated_payout_m").value):
            raise ValueError(f"a {out['max_payout_m']:.2f} m line cannot deliver")
        out["saved_at"] = limit.get("saved_at")
        return out

    def _save_position(self, force=False):
        """Keep the line position with the limits: the estimate starts from it
        after a restart instead of assuming the line is wound up."""
        path = self._limits_path()
        if not (path and self.limit) or (not force and self._saved_payout is not None
                                         and abs(self._saved_payout - self.payout) < 0.005):
            return True
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"limit": self.limit, "position_m": round(max(0.0, self.payout), 4)},
                          f, allow_nan=False)
            os.replace(tmp, path)
        except OSError as error:
            self.get_logger().warning(f"winch position not saved: {error}")
            self.cal_reason = f"not saved: {error}"
            return False
        self._saved_payout = self.payout
        return True

    def _on_calibration(self, msg):
        try:
            data = json.loads(msg.data)
            action = str(data.get("action", ""))
        except (ValueError, AttributeError):
            self.cal_reason = "refused: not a calibration request"
            return
        self.cal_reason = self.calibrate(action, data.get("length_m"))
        if self.cal_reason:
            self.get_logger().warning(f"winch calibration {action}: {self.cal_reason}")

    def calibrate(self, action, length_m=None):
        """One calibration step; "" when done, else why it was refused."""
        if self.backend != "l298n":
            return f"refused: winch limits are calibrated on the L298N backend, not {self.backend}"
        if action == "end":
            if self.calibrating():
                self._end_calibration("")
            return ""
        if self.mission_active():
            return "refused: a mission is running"
        if self.state in ("LOWERING", "STOWING", "FAULT"):
            return f"refused: the winch is {self.state}"
        if action == "begin":
            self.cal_until = self._now() + float(self.get_parameter("calibration_timeout_s").value)
            self.cal_zeroed, self.cal_run_s = False, 0.0
            self.get_logger().info("winch calibration open: hand drive limits lifted")
            return ""
        if not self.calibrating():
            return "refused: start a calibration first"
        if action == "set_min":
            self.payout, self.cal_run_s, self.cal_zeroed = 0.0, 0.0, True
            if self.state in ("AT_LIMIT", "AT_GROUND"):
                self.state = "RELEASED" if self.released else "IDLE"
            self.get_logger().info("winch wound-up limit marked")
            return ""
        if action != "set_max":
            return f"refused: unknown calibration step {action!r}"
        if not self.cal_zeroed:
            return "refused: mark the wound-up limit first"
        try:
            length = float(length_m)
        except (TypeError, ValueError):
            return "refused: enter the line length measured at the paid-out limit"
        if self.cal_run_s <= 1.0:
            return "refused: pay the line out from the wound-up mark first"
        try:
            limit = self._valid_limit({"max_payout_m": length, "line_speed_mps": length / self.cal_run_s,
                                       "stroke_s": self.cal_run_s,
                                       "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        except ValueError as error:
            return f"refused: {error}"
        previous = (self.limit, self.payout, self.limit_source)
        self.limit, self.payout = limit, length
        self.limit_source = "GCS calibration"
        if not self._save_position(force=True):
            self.limit, self.payout, self.limit_source = previous
            return "refused: " + self.cal_reason
        self.get_logger().info(f"winch paid-out limit {length:.2f} m, {limit['stroke_s']:.1f} s "
                               f"of motor run, {limit['line_speed_mps']:.3f} m/s")
        return ""

    def _end_calibration(self, reason):
        self.cal_until = None
        if self.limit:
            self.payout = max(0.0, min(self.payout, self.max_payout()))
            self._save_position()
        else:
            self.payout = max(0.0, self.payout)
        self.cal_reason = reason
        self.get_logger().info("winch calibration closed" + (f": {reason}" if reason else ""))

    def destroy_node(self):
        if getattr(self, "motor", None) is not None:
            self.motor.close()
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
        if self.backend == "l298n":
            if self.motor is None:
                if action in ("lower", "stow"):
                    self._set_fault(self.fault or "l298n winch unavailable")
                return
            lower = 1 if int(self.get_parameter("l298n_lower_direction").value) >= 0 else -1
            # A gravity hook has no release actuator: release only stops the reel.
            self.motor.drive({"lower": lower, "stow": -lower}.get(action, 0))
            return
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
        self._unacked = None
        gen = self._mav_gen
        req = CommandLong.Request()
        req.command = MAV_CMD_DO_WINCH
        req.param1 = 1.0                                   # instance
        if action == "lower":
            req.param2 = float(WINCH_RELATIVE_LENGTH_CONTROL)
            req.param3 = max(0.0, self.max_payout() - self.payout)
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
        if (reply is not None and not reply.success and int(reply.result) == 0
                and action in ("lower", "stow") and self._measured() is not None):
            # MAVROS gives up waiting for the COMMAND_ACK with success false
            # and result 0, ACCEPTED's code: no answer, not a refusal. In r15
            # and r16 (26 Oct) the simulator's FC reported lowering 45 ms after
            # this was raised as a refusal and the mission failed into RTL.
            # With the line measured, its motion decides (integrate()).
            self._unacked = (action, self._now(), self._measured())
            self.get_logger().warning(f"DO_WINCH {action}: no acknowledgement from the "
                                      f"FC; watching the measured line")
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
        return self.payout >= self.max_payout()

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
        if self.backend == "l298n":
            self._sync_l298n(dt)
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
        if self._unacked is not None and self._check_unacked():
            return
        lower_rate = float(self.get_parameter("payout_rate_mps").value)
        stow_rate = float(self.get_parameter("stow_rate_mps").value)
        if self.backend == "l298n":
            # One motor at one duty both ways: a stow timed at the faster
            # stow_rate_mps stopped with a third of the line still out.
            lower_rate = stow_rate = self.line_speed()
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
                self.max_payout(),
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

    def _check_unacked(self):
        """An unacknowledged DO_WINCH: accepted once the measured line moves
        its way, a fault if it has not within unacked_motion_s. True if it
        faulted."""
        action, t0, start = self._unacked
        measured = self._measured()
        moved = None if measured is None else (
            measured - start if action == "lower" else start - measured)
        if moved is not None and moved >= 0.05:
            self._unacked = None
            self._mav_accepted = True
            self.get_logger().info(f"DO_WINCH {action}: unacknowledged, but the measured "
                                   f"line moved {moved:.2f} m its way; taken as accepted")
            return False
        wait = float(self.get_parameter("unacked_motion_s").value)
        if self._now() - t0 >= wait:
            self._unacked = None
            self._set_fault(f"flight controller did not acknowledge DO_WINCH {action} "
                            f"and the measured line did not move in {wait:.0f} s")
            return True
        return False

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
        limit = self.max_payout()
        if self.state == "LOWERING" and measured >= limit - float(self.get_parameter("limit_window_m").value):
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
            "rc_manual": getattr(self, "manual", 0),
            "rc_manual_ready": getattr(self, "rc_ready", False),
            "rc_manual_reason": getattr(self, "rc_reason", ""),
            "mission_active": self.mission_active() if self.backend == "l298n" else None,
            "payout_basis": ("measured N20 encoder travel" if self.gpio is not None
                             else "measured winch joint" if self._measured() is not None
                             else "motor run time at the calibrated line speed; no encoder" if self.limit
                             else "integrated commanded motor rate; no encoder"),
            "limit_m": round(self.max_payout(), 3),
            "limits": None if not self.limit else dict(self.limit, source=self.limit_source),
            "calibration": {
                "active": self.calibrating(), "zeroed": self.cal_zeroed,
                "run_s": round(self.cal_run_s, 2),
                "remaining_s": (None if not self.calibrating()
                                else round(max(0.0, self.cal_until - self._now()), 1)),
                "reason": self.cal_reason},
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
