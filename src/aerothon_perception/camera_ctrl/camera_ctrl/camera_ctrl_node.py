#!/usr/bin/env python3
"""Camera pointing as a commanded, CONFIRMED state (PHASE_PLAN.md Phase 2).

WHY THIS EXISTS
    CURRENT_PROGRESS_HANDOFF.md: the start QR sits on the ground ~1 m ahead of
    the spawn point, the mission holds at (0,0,5), and nothing ever commands
    the camera downward. The detector was never the problem — the camera was
    pointed at a wall and the sky. No amount of QR tuning fixes an aim error.

    So camera orientation stops being an assumption and becomes state:
    commanded, read back from the actual joint, and gated on before any
    perception stage that depends on it.

NAMED POSES
    FORWARD   0 deg    corridor navigation
    BANNER  -20 deg    banner detection from above corridor altitude
    GROUND  -35 deg    a banner laid flat in front of the corridor
    NADIR   -90 deg    start-QR scan, lawnmower search, winch drop, landing
    ALIGN   -45 deg    intermediate, target centring during descent

INTERFACE
    sub   /camera/set_pose      std_msgs/String   "FORWARD" | "NADIR" | "ALIGN"
                                                  or a raw angle in degrees
    sub   /joint_states         sensor_msgs/JointState   read-back (sim)
    sub   /mavros/gimbal_control/device/attitude_status  read-back (hardware)
    pub   /gimbal/cmd_pitch     std_msgs/Float64  radians, sim backend
    pub   /camera/pose_state    std_msgs/String   JSON, 10 Hz

    /camera/pose_state fields:
        requested       pose name, or "" before the first command
        requested_rad   commanded joint angle
        actual_rad      measured joint angle (null when never observed)
        error_deg       |actual - requested| in degrees
        settled         measurement within tolerance, held long enough
        stale           no read-back within stale_after_s
        age_s           seconds since the last read-back
        rate_dps        how fast the measured angle is changing, deg/s over
                        the last rate_window_s of read-backs (null until two
                        read-backs span rate_min_span_s)

    `settled` is the only field a mission stage should gate on. It is false
    until the joint has been MEASURED in position — never inferred from the
    fact that a command was sent.

BACKENDS
    backend:=sim      publish radians to /gimbal/cmd_pitch (Gazebo
                      JointPositionController), read back from /joint_states
    backend:=mavlink  MAV_CMD_DO_MOUNT_CONTROL via /mavros/cmd/command, read
                      back from the flight controller's mount attitude
                      (GIMBAL_DEVICE_ATTITUDE_STATUS) whenever it reports one.
                      The aircraft's tilt is a hobby servo on the Pixhawk: it
                      has no position feedback, and whether the flight
                      controller streams a mount attitude for it depends on
                      its configuration. Without one this backend used to
                      read back from /joint_states -- which only Gazebo
                      publishes -- so `settled` could never become true and
                      the mission would have waited at its first camera
                      command. Where no attitude arrives the servo is taken
                      to be at a new angle `servo_settle_s` after it was
                      commanded, and pose_state says so: readback "timed".
    Same topic interface either way, so the mission tree does not care which
    airframe it is flying.

TILT CALIBRATION (tilt_calibration.py)
    The angle the mission asks for is not the output sent: a recorded
    calibration maps it to the output that puts THIS servo at that angle.
    The GCS records one with the operator watching the camera:

    sub   /camera/calibration/jog      std_msgs/String   a raw output
    sub   /camera/calibration          std_msgs/String   {"points": {pose: output}}
                                                         or {"points": null} to clear
    pub   /camera/calibration/applied  std_msgs/String   JSON, latched

    A calibration is saved to `calibration_file` and loaded at startup.
    pose_state adds `output` (what was sent), `output_unit` (deg or us), the
    output's range and `calibrated`.

THE SERVO ITSELF (backend:=mavlink, fc_output:=servo; the aircraft, 27 Oct)
    No mount on the FC: the tilt servo sits on an FC output (`servo_channel`,
    SERVO5) whose SERVOn_FUNCTION is 0, and the Pi sets its pulse width with
    MAV_CMD_DO_SET_SERVO. Outputs are microseconds within servo_pwm_min..max;
    uncalibrated, forward is servo_pwm_forward and each degree down
    servo_pwm_per_deg less. The FC's lean compensation and level calibration
    play no part (a servo mount on this aircraft read it 31 deg nose-up on
    the bench and squeezed the three poses into the bottom of the travel).

    The receiver keeps its say: `rc_tilt_channel` (read from /aerothon/rc/in)
    tilts the camera whenever no mission runs -- once the stick or switch has
    moved since the Pi last commanded the camera, so a Camera cal pose or the
    end of a mission is not undone by a stick left where it was. During a
    mission the receiver is ignored. The channel is an ANGLE, not a pulse
    width: rc_tilt_low_us is straight down, rc_tilt_high_us forward, the
    middle 45 deg down, and that angle goes through the Camera cal like a GCS
    pose, so a three-position switch lands on the three recorded poses (30 Oct
    2026: passed through as a pulse width it missed every calibrated pose).
"""

import json
import math
import os
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, String

from camera_ctrl import tilt_calibration

try:
    from mavros_msgs.msg import GimbalDeviceAttitudeStatus
    from mavros_msgs.srv import CommandLong
    _HAVE_MAVROS = True
except ImportError:                       # sim-only installs
    _HAVE_MAVROS = False
try:
    from mavros_msgs.msg import RCIn
except ImportError:
    RCIn = None

MAV_CMD_DO_MOUNT_CONTROL = 205
MAV_CMD_DO_SET_SERVO = 183
MAV_MOUNT_MODE_MAVLINK_TARGETING = 2
# Mission states in which no autonomous flight runs (winch_ctrl's list): the
# receiver may move the camera only then.
MISSION_IDLE_STATES = frozenset({"", "IDLE", "WAITING", "COMPLETED", "FAILED", "ABORTED"})

NAMED_POSES_DEG = {
    "FORWARD": 0.0,
    "NADIR": -90.0,
    "ALIGN": -45.0,
    # The rulebook requires the banner to be identified and the aircraft
    # aligned BEFORE descending to corridor altitude. From 5 m, a gate a few
    # metres ahead is entirely below a level camera -- a live run swept 271
    # degrees past it. Looking slightly down puts it in frame from the scan
    # altitude, so the rulebook order can be followed rather than worked
    # around by descending first.
    "BANNER": -20.0,
    # A banner laid flat in front of the corridor (organiser clarification).
    # The frame spans +-18 deg about this: from gate height (3 m) it covers
    # 2.3-10 m of ground ahead, from the 5 m return-search height 3.8-16 m,
    # so the sheet is in frame both squared up and on the return approach.
    # -30 put it on the bottom edge from 5 m up, 5 m out.
    "GROUND": -35.0,
    # The return-gate search's second tilt for a HUNG board: from the 5 m
    # look height a board 3-4 m away sits 31-40 deg below the horizon, under
    # the BANNER frame (shipped_20kmh_r5). ALIGN's angle, but the banner
    # detector runs in it; ALIGN stays the QR stages' and closed to it.
    "BANNER_DOWN": -45.0,
}


def _sensor_qos(depth=10):
    """Best-effort: /joint_states is published reliably at ~785 Hz, and a
    reliable subscriber there just builds backpressure and drops anyway."""
    return QoSProfile(depth=depth,
                      history=QoSHistoryPolicy.KEEP_LAST,
                      reliability=QoSReliabilityPolicy.BEST_EFFORT)


class CameraCtrl(Node):
    def __init__(self, **kwargs):
        super().__init__("camera_ctrl", **kwargs)

        p = self.declare_parameter
        p("backend", "sim")                 # sim | mavlink
        p("joint_name", "webcam_pitch_joint")
        p("tolerance_deg", 2.0)
        p("settle_samples", 5)              # consecutive in-tolerance samples
        p("settle_hold_s", 0.20)            # ...held at least this long
        p("stale_after_s", 1.0)
        p("publish_rate_hz", 10.0)
        p("command_repeat_s", 0.5)          # re-send until settled
        p("startup_pose", "FORWARD")
        p("external_joint_feedback", False)
        p("servo_settle_s", 1.0)            # mavlink, no attitude: time to angle
        # rate_dps: the read-back's own motion, so a consumer that only needs
        # a steady, MEASURED angle (not the requested one) can tell a slew
        # from a mount holding still while the airframe pitches under it.
        p("rate_window_s", 0.3)
        p("rate_min_span_s", 0.05)
        # The recorded tilt calibration; "" keeps none (output = angle).
        p("calibration_file", "")
        # backend:=mavlink: "mount" sends MAV_CMD_DO_MOUNT_CONTROL to an FC
        # mount; "servo" sets an FC output's pulse width (see THE SERVO ITSELF).
        p("fc_output", "mount")
        p("servo_channel", 5)
        p("servo_pwm_min", 800)
        p("servo_pwm_max", 2200)
        p("servo_pwm_forward", 1500.0)
        p("servo_pwm_per_deg", 500.0 / 90.0)
        p("rc_tilt_channel", 0)             # receiver channel for the tilt; 0 = none
        p("rc_takeover_us", 30)             # stick movement that takes the camera back
        p("rc_timeout_s", 0.5)
        p("rc_tilt_low_us", 1000)           # receiver pulse for straight down (-90 deg)
        p("rc_tilt_high_us", 2000)          # receiver pulse for forward (0 deg)
        p("rc_tilt_reversed", False)        # low pulse forward, high straight down

        self.backend = self.get_parameter("backend").value
        self.joint_name = self.get_parameter("joint_name").value
        self.external_joint_feedback = self.get_parameter("external_joint_feedback").value is True

        self.requested_name = ""
        self.requested_rad = None
        self._explicit_request = False
        self.actual_rad = None
        self.last_reading_t = None
        self._in_tolerance_count = 0
        self._in_tolerance_since = None
        self._last_command_t = None
        self._target_t = None               # when the current target was set
        self._prev_rad = 0.0                # the target before it
        self._mount_t = None                # last mount attitude from the FC
        self._readings = deque()            # (t, rad) within rate_window_s
        self.calibration = None             # {pose: output}, or None
        self.calibration_source = "none recorded"
        self._raw_output = None             # a jog's or the receiver's output
        self._rc = None                     # (channels, receipt time)
        self._rc_hold = None                # receiver value when the Pi last commanded
        self._mission_state = ""

        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_cal_applied = self.create_publisher(String, "/camera/calibration/applied", latched)
        self._load_calibration()
        self.create_subscription(String, "/camera/calibration", self._on_calibration, latched)
        self.create_subscription(String, "/camera/calibration/jog", self._on_jog, 10)
        self.create_subscription(String, "/camera/set_pose", self._on_set_pose, 10)
        if self.backend == "sim" or self.external_joint_feedback:
            self.create_subscription(JointState, "/joint_states",
                                     self._on_joint_states, _sensor_qos())

        self.pub_cmd = self.create_publisher(Float64, "/gimbal/cmd_pitch", 10)
        self.pub_state = self.create_publisher(String, "/camera/pose_state", 10)

        self.cli_cmd = None
        if self.backend == "mavlink":
            if not _HAVE_MAVROS:
                self.get_logger().error(
                    "backend=mavlink but mavros_msgs is unavailable")
            else:
                self.cli_cmd = self.create_client(CommandLong, "/mavros/cmd/command")
                if not self.servo_output():
                    self.create_subscription(
                        GimbalDeviceAttitudeStatus,
                        "/mavros/gimbal_control/device/attitude_status",
                        self._on_mount_status, _sensor_qos())
        if self.servo_output() and int(self.get_parameter("rc_tilt_channel").value) > 0:
            if RCIn is not None:
                # rc_in_bridge: the FC's channels even with chancount 0.
                self.create_subscription(RCIn, "/aerothon/rc/in", self._on_rc,
                                         qos_profile_sensor_data)
            self.create_subscription(String, "/mission/state", self._on_mission_state, 10)

        rate = float(self.get_parameter("publish_rate_hz").value)
        self.create_timer(1.0 / rate, self._tick)

        startup = self.get_parameter("startup_pose").value
        if startup:
            self.request(startup)

        self.get_logger().info(
            f"camera_ctrl up; backend={self.backend} joint={self.joint_name} "
            f"startup={startup}")

    # ------------------------------------------------------------------ #
    # commanding
    # ------------------------------------------------------------------ #
    def _on_set_pose(self, msg: String):
        self.request(msg.data.strip())

    def request(self, target: str):
        """Accept a named pose or a raw angle in degrees."""
        key = target.upper()
        if key in NAMED_POSES_DEG:
            deg = NAMED_POSES_DEG[key]
            name = key
        else:
            try:
                deg = float(target)
                # The GCS camera buttons send degrees; an angle that is a
                # named pose must carry that name or the detector gates
                # (NADIR/ALIGN/FORWARD) never open.
                name = next((k for k, v in NAMED_POSES_DEG.items()
                             if abs(v - deg) < 1e-6), f"{deg:.1f}deg")
            except ValueError:
                self.get_logger().warning(
                    f"unknown camera pose '{target}'; "
                    f"expected one of {sorted(NAMED_POSES_DEG)} or a number")
                return

        new_rad = math.radians(deg)
        self._explicit_request = True
        if self.requested_rad is not None and self._raw_output is None and \
                abs(new_rad - self.requested_rad) < 1e-6 and name == self.requested_name:
            return                                  # already commanding this

        self._raw_output = None
        self._rc_hold = self._rc_value()
        self._target(name, new_rad)
        self.get_logger().info(f"camera pose -> {name} ({deg:.1f} deg, "
                               f"output {self.output():.1f} {self.output_unit()})")
        self._send()

    def _target(self, name, new_rad):
        self.requested_name = name
        self._prev_rad = self.requested_rad if self.requested_rad is not None else 0.0
        self.requested_rad = new_rad
        self._target_t = self._now()
        # A new target invalidates any previous settle: the joint has not been
        # measured at the NEW angle yet.
        self._in_tolerance_count = 0
        self._in_tolerance_since = None
        self._last_command_t = None
        # Timed readback starts only once the FC has accepted THIS target.
        self._cmd_gen = getattr(self, '_cmd_gen', 0) + 1
        self._accepted_t = None

    def servo_output(self):
        """The Pi sets the servo's pulse width itself (THE SERVO ITSELF)."""
        return self.backend == "mavlink" and self.get_parameter("fc_output").value == "servo"

    def output_unit(self):
        return "us" if self.servo_output() else "deg"

    def output_limits(self):
        if self.servo_output():
            return (float(self.get_parameter("servo_pwm_min").value),
                    float(self.get_parameter("servo_pwm_max").value))
        return tilt_calibration.OUTPUT_MIN_DEG, tilt_calibration.OUTPUT_MAX_DEG

    def _points(self):
        """The calibration, or for the servo the uncalibrated straight line."""
        if self.calibration or not self.servo_output():
            return self.calibration
        forward = float(self.get_parameter("servo_pwm_forward").value)
        per_deg = float(self.get_parameter("servo_pwm_per_deg").value)
        return {pose: forward + per_deg * angle for pose, angle in tilt_calibration.POSES.items()}

    def output(self):
        """What goes to the servo: a jog's or the receiver's raw output, or
        the requested angle through the calibration."""
        if self._raw_output is not None:
            return self._raw_output
        if self.requested_rad is None:
            return None
        return tilt_calibration.output_for(math.degrees(self.requested_rad), self._points(),
                                           *self.output_limits())

    def _send(self):
        if self.requested_rad is None:
            return
        if self.backend == "mavlink":
            sent = self._send_set_servo() if self.servo_output() else self._send_mavlink()
            if not sent:
                return          # not sent: try again next tick, not in 1 s
        else:
            self.pub_cmd.publish(Float64(data=math.radians(self.output())))
        self._last_command_t = self._now()

    # ------------------------------------------------------------------ #
    # the receiver (fc_output:=servo, rc_tilt_channel)
    # ------------------------------------------------------------------ #
    def _on_rc(self, msg):
        self._rc = (list(msg.channels), self._now())

    def _on_mission_state(self, msg):
        self._mission_state = str(msg.data).split(":")[0].strip()

    def mission_active(self):
        return self._mission_state not in MISSION_IDLE_STATES

    def _rc_value(self):
        """The tilt channel's fresh, valid pulse width, or None."""
        ch = int(self.get_parameter("rc_tilt_channel").value)
        if ch <= 0 or self._rc is None:
            return None
        channels, t = self._rc
        if self._now() - t > float(self.get_parameter("rc_timeout_s").value):
            return None
        if not 0 < ch <= len(channels) or not 900 <= int(channels[ch - 1]) <= 2200:
            return None
        return int(channels[ch - 1])

    def _rc_angle(self, rc):
        """The receiver pulse as a tilt angle: low straight down, high forward
        (or the reverse), clamped to the three poses' span."""
        low = float(self.get_parameter("rc_tilt_low_us").value)
        high = float(self.get_parameter("rc_tilt_high_us").value)
        share = min(1.0, max(0.0, (rc - low) / (high - low))) if high != low else 0.5
        if self.get_parameter("rc_tilt_reversed").value is True:
            share = 1.0 - share
        down, forward = tilt_calibration.POSES["NADIR"], tilt_calibration.POSES["FORWARD"]
        return down + (forward - down) * share

    def _rc_passthrough(self):
        """The receiver's tilt channel onto the camera while no mission runs,
        once it has moved since the Pi last commanded the camera."""
        if not self.servo_output() or self.mission_active():
            return
        rc = self._rc_value()
        if rc is None:
            return
        if self._rc_hold is not None:
            if abs(rc - self._rc_hold) < int(self.get_parameter("rc_takeover_us").value):
                return
            self._rc_hold = None
            self.get_logger().info(f"camera tilt from the receiver (channel "
                                   f"{self.get_parameter('rc_tilt_channel').value})")
        angle = self._rc_angle(rc)
        if self.requested_name == "RC" and self._raw_output is None and \
                self.requested_rad is not None and \
                abs(math.degrees(self.requested_rad) - angle) < 0.5:
            return
        self._raw_output = None                     # through the calibration
        self._target("RC", math.radians(angle))
        self._send()

    def _send_set_servo(self):
        """MAV_CMD_DO_SET_SERVO: the servo output's pulse width, microseconds."""
        if self.cli_cmd is None or not self.cli_cmd.service_is_ready():
            return False
        req = CommandLong.Request()
        req.command = MAV_CMD_DO_SET_SERVO
        req.param1 = float(int(self.get_parameter("servo_channel").value))
        req.param2 = float(round(self.output()))
        gen = getattr(self, '_cmd_gen', 0)
        future = self.cli_cmd.call_async(req)
        if future is not None and hasattr(future, 'add_done_callback'):
            future.add_done_callback(lambda f, gen=gen: self._on_command_reply(f, gen))
        return True

    # ------------------------------------------------------------------ #
    # tilt calibration
    # ------------------------------------------------------------------ #
    def _on_jog(self, msg):
        """A raw output from the calibration page: sent as it is, so the
        operator can find the output that puts the camera at a pose."""
        try:
            output = tilt_calibration.clamp_output(float(msg.data), *self.output_limits())
        except ValueError:
            self.get_logger().warning(f"camera jog '{msg.data}' is not a number")
            return
        self._explicit_request = True
        self._raw_output = output
        self._rc_hold = self._rc_value()
        self._target("CALIBRATION",
                     math.radians(tilt_calibration.angle_for(output, self._points())))
        self.get_logger().info(f"camera calibration output -> {output:.1f} {self.output_unit()}")
        self._send()

    def _validate(self, points):
        return tilt_calibration.validate(points, *self.output_limits(), unit=self.output_unit())

    def _load_calibration(self):
        path = self._calibration_path()
        if not path:
            self._report_calibration("")
            return
        try:
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
            # A calibration recorded for the other output means nothing here:
            # mount degrees are not the servo's microseconds.
            if saved.get("points") is not None and saved.get("unit", "deg") != self.output_unit():
                raise ValueError(f"recorded in {saved.get('unit', 'deg')}, this output "
                                 f"is in {self.output_unit()}; calibrate again")
            if saved.get("points") is not None:
                self.calibration = self._validate(saved["points"])
            self.calibration_source = f"saved calibration ({path})"
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError, TypeError) as error:
            self.get_logger().warning(f"saved camera calibration ignored: {error}")
            self._report_calibration(f"saved calibration ignored: {error}")
            return
        self._report_calibration("")

    def _calibration_path(self):
        path = str(self.get_parameter("calibration_file").value or "")
        return os.path.expanduser(path) if path else ""

    def _on_calibration(self, msg):
        """Apply a calibration from the GCS now, and keep it."""
        try:
            data = json.loads(msg.data)
            raw = data.get("points")
            points = None if raw is None else self._validate(raw)
        except (ValueError, AttributeError, TypeError) as error:
            self.get_logger().warning(f"camera calibration refused: {error}")
            self._report_calibration(f"refused: {error}")
            return
        path = self._calibration_path()
        reason = ""
        if path:
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({"points": points, "unit": self.output_unit(),
                               "saved_at": data.get("saved_at")}, f, allow_nan=False)
                os.replace(tmp, path)
            except OSError as error:
                reason = f"applied, not saved: {error}"
        else:
            reason = "applied, not saved: no calibration_file"
        self.calibration = points
        self.calibration_source = "GCS calibration" if points else "cleared at the GCS"
        self.get_logger().info(f"camera calibration -> {points}")
        self._report_calibration(reason)
        if self.requested_rad is not None and self._raw_output is None:
            # The same angle now needs a different output.
            self._in_tolerance_count, self._in_tolerance_since = 0, None
            self._cmd_gen = getattr(self, '_cmd_gen', 0) + 1
            self._accepted_t = None
            self._send()

    def _report_calibration(self, reason):
        self.pub_cal_applied.publish(String(data=json.dumps({
            "points": self.calibration, "unit": self.output_unit(),
            "source": self.calibration_source, "reason": reason}, separators=(",", ":"))))

    def _send_mavlink(self):
        """True when a command went out. Its reply is checked: with timed
        readback, a command lost before MAVROS was ready or rejected by the FC
        used to be reported settled 1 s later while the camera never moved."""
        if self.cli_cmd is None or not self.cli_cmd.service_is_ready():
            return False
        req = CommandLong.Request()
        req.command = MAV_CMD_DO_MOUNT_CONTROL
        req.param1 = float(self.output())                      # pitch, degrees
        req.param2 = 0.0                                       # roll
        req.param3 = 0.0                                       # yaw
        req.param7 = float(MAV_MOUNT_MODE_MAVLINK_TARGETING)
        gen = getattr(self, '_cmd_gen', 0)
        future = self.cli_cmd.call_async(req)
        if future is not None and hasattr(future, 'add_done_callback'):
            future.add_done_callback(lambda f, gen=gen: self._on_command_reply(f, gen))
        return True

    def _on_command_reply(self, future, gen):
        if gen != getattr(self, '_cmd_gen', 0):
            return              # a reply about a superseded target
        try:
            reply = future.result()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warning(f"camera mount command failed: {exc}")
            return
        if reply is not None and reply.success and int(reply.result) == 0:
            if getattr(self, '_accepted_t', None) is None:
                self._accepted_t = self._now()
        else:
            self.get_logger().warning(
                f"camera mount command not accepted (result "
                f"{getattr(reply, 'result', None)}); retrying")

    # ------------------------------------------------------------------ #
    # read-back
    # ------------------------------------------------------------------ #
    def _on_joint_states(self, msg: JointState):
        if self.backend != "sim" and not self.external_joint_feedback:
            return
        try:
            idx = list(msg.name).index(self.joint_name)
        except ValueError:
            return
        if idx >= len(msg.position):
            return
        self._observe(float(msg.position[idx]))

    def _on_mount_status(self, msg):
        """Pitch from the flight controller's mount attitude (up positive,
        so down is negative, as here). A servo mount reports the output it
        was sent, so the calibration turns it back into the camera's angle."""
        q = msg.q
        self._mount_t = self._now()
        output = math.degrees(math.asin(max(-1.0, min(1.0, 2.0 * (q.w * q.y - q.z * q.x)))))
        self._observe(math.radians(tilt_calibration.angle_for(output, self.calibration)))

    def readback(self):
        if self.backend == "sim" or self.external_joint_feedback:
            return "joint"
        fresh = (self._mount_t is not None and self._now() - self._mount_t
                 <= float(self.get_parameter("stale_after_s").value))
        return "mount" if fresh else "timed"

    def _observe_timed(self):
        """No feedback: at the new angle once the servo has had time to get
        there, at the old one until then."""
        if self.requested_rad is None or self._target_t is None:
            return
        accepted = getattr(self, '_accepted_t', None)
        late = accepted is not None and self._now() - accepted >= float(
            self.get_parameter("servo_settle_s").value)
        self._observe(self.requested_rad if late else self._prev_rad)

    def _observe(self, rad):
        if not math.isfinite(rad):
            return
        self.actual_rad = rad
        self.last_reading_t = self._now()
        self._readings.append((self.last_reading_t, rad))
        window = float(self.get_parameter("rate_window_s").value)
        while self._readings and self.last_reading_t - self._readings[0][0] > window:
            self._readings.popleft()
        if self.requested_rad is None:
            # Observe an already-positioned mount without moving it on Connect.
            named = min(NAMED_POSES_DEG, key=lambda k: abs(math.radians(NAMED_POSES_DEG[k])-rad))
            if abs(math.radians(NAMED_POSES_DEG[named])-rad) > math.radians(float(self.get_parameter('tolerance_deg').value)):
                return
            self.requested_name = named
            self.requested_rad = math.radians(NAMED_POSES_DEG[named])
        tol = math.radians(float(self.get_parameter("tolerance_deg").value))
        if abs(rad - self.requested_rad) <= tol:
            self._in_tolerance_count += 1
            if self._in_tolerance_since is None:
                self._in_tolerance_since = self.last_reading_t
        else:
            self._in_tolerance_count = 0
            self._in_tolerance_since = None

    # ------------------------------------------------------------------ #
    def _now(self):
        return self.get_clock().now().nanoseconds / 1e9

    def is_settled(self):
        if self.requested_rad is None or self.actual_rad is None:
            return False
        if self.is_stale():
            return False
        if self._in_tolerance_count < int(self.get_parameter("settle_samples").value):
            return False
        if self._in_tolerance_since is None:
            return False
        hold = float(self.get_parameter("settle_hold_s").value)
        return (self._now() - self._in_tolerance_since) >= hold

    def rate_dps(self):
        """|change| of the measured angle over the recent window, deg/s."""
        if len(self._readings) < 2:
            return None
        (t0, a0), (t1, a1) = self._readings[0], self._readings[-1]
        if t1 - t0 < float(self.get_parameter("rate_min_span_s").value):
            return None
        return abs(math.degrees(a1 - a0)) / (t1 - t0)

    def is_stale(self):
        if self.last_reading_t is None:
            return True
        stale_after = float(self.get_parameter("stale_after_s").value)
        return (self._now() - self.last_reading_t) > stale_after

    def _tick(self):
        self._rc_passthrough()
        if self.backend == "mavlink" and self.readback() == "timed":
            self._observe_timed()
        # Keep re-issuing until the joint is measured in position. The Gazebo
        # position controller and a real servo can both miss a single command.
        if getattr(self, '_explicit_request', True) and self.requested_rad is not None and not self.is_settled():
            repeat = float(self.get_parameter("command_repeat_s").value)
            if self._last_command_t is None or \
                    (self._now() - self._last_command_t) >= repeat:
                self._send()

        err_deg = None
        if self.actual_rad is not None and self.requested_rad is not None:
            err_deg = abs(math.degrees(self.actual_rad - self.requested_rad))

        age = None if self.last_reading_t is None else self._now() - self.last_reading_t

        payload = {
            "requested": self.requested_name,
            "requested_rad": self.requested_rad,
            "actual_rad": self.actual_rad,
            "error_deg": err_deg,
            "settled": self.is_settled(),
            "stale": self.is_stale(),
            "age_s": age,
            "readback": self.readback(),
            "rate_dps": self.rate_dps(),
            "output": self.output(),
            "output_unit": self.output_unit(),
            "output_min": self.output_limits()[0],
            "output_max": self.output_limits()[1],
            "calibrated": self.calibration is not None,
        }
        self.pub_state.publish(String(data=json.dumps(payload)))


def main():
    rclpy.init()
    node = CameraCtrl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
