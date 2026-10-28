#!/usr/bin/env python3
"""The GCS's camera tilt and winch limit calibrations (operator, 26 Oct 2026).

Camera: nothing says which servo output puts the camera at which angle, so
the operator sends a pose, watches the camera, nudges the output until it is
really at forward / 45 deg / straight down, and records each. Every angle the
mission asks for then goes out through those three points.

Winch (L298N, no encoder): the operator winds the line in with RC6 to where
it should stop and marks it, pays it out to where it should stop and marks
that with the measured line. Those limits then hold for RC6 hand drive, the
mechanism tests and the mission, whose release height follows the line.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_gcs_calibrations.py -v
"""

import json
import math
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for package in (("aerothon_perception", "camera_ctrl"), ("aerothon_payload", "winch_ctrl"),
                ("aerothon_mission", "mission_bt")):
    sys.path.insert(0, os.path.join(ROOT, "src", *package))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
import rclpy
from rclpy.parameter import Parameter
from std_msgs.msg import String

from camera_ctrl import tilt_calibration as T
from camera_ctrl.camera_ctrl_node import CameraCtrl
from winch_ctrl.l298n import FORWARD, REVERSE, STOP, L298NDriver
from winch_ctrl.winch_node import WinchNode
from test_l298n_winch import FakeLgpio, FakeRC

# A servo that is off and short: straight down needs -78, forward +6.
MEASURED = {"FORWARD": 6.0, "ALIGN": -38.0, "NADIR": -78.0}


@pytest.fixture(scope="module", autouse=True)
def ros():
    owns = not rclpy.ok()
    if owns:
        rclpy.init()
    yield
    if owns and rclpy.ok():
        rclpy.shutdown()


# ---------------------------------------------------------------- mapping
def test_no_calibration_sends_the_angle_itself():
    assert T.output_for(-90, None) == -90
    assert T.angle_for(-35, None) == -35


def test_each_recorded_pose_gets_its_recorded_output():
    points = T.validate(MEASURED)
    for pose, angle in T.POSES.items():
        assert T.output_for(angle, points) == pytest.approx(MEASURED[pose])
        assert T.angle_for(MEASURED[pose], points) == pytest.approx(angle)


def test_other_poses_follow_the_line_through_their_neighbours():
    points = T.validate(MEASURED)
    # BANNER -20: between forward (0 -> 6) and 45 down (-45 -> -38).
    assert T.output_for(-20, points) == pytest.approx(6 + (-38 - 6) * 20 / 45)
    # GROUND -35 and BANNER_DOWN -45 too; +10 extends the forward segment.
    assert T.output_for(-35, points) == pytest.approx(6 + (-38 - 6) * 35 / 45)
    assert T.output_for(10, points) == pytest.approx(6 + 44 * 10 / 45)
    for angle in (-90, -60, -35, -20, 0, 10):
        assert T.angle_for(T.output_for(angle, points), points) == pytest.approx(angle)


def test_a_reversed_servo_is_still_a_calibration():
    points = T.validate({"FORWARD": -80.0, "ALIGN": -30.0, "NADIR": 20.0})
    assert T.output_for(-90, points) == pytest.approx(20)
    assert T.output_for(-20, points) == pytest.approx(-80 + 50 * 20 / 45)


@pytest.mark.parametrize("data,why", [
    ({"FORWARD": 0, "ALIGN": -45}, "no output recorded for NADIR"),
    ({"FORWARD": 0, "ALIGN": -45, "NADIR": -95}, "outside the"),
    ({"FORWARD": 0, "ALIGN": -45, "NADIR": -45.5}, "same output"),
    ({"FORWARD": 0, "ALIGN": -60, "NADIR": -40}, "one direction"),
    ({"FORWARD": 0, "ALIGN": -45, "NADIR": -90, "UP": 30}, "unknown pose"),
    ({"FORWARD": True, "ALIGN": -45, "NADIR": -90}, "number"),
])
def test_impossible_calibrations_are_refused_with_the_reason(data, why):
    with pytest.raises(ValueError, match=why):
        T.validate(data)


def test_the_output_is_clamped_to_the_mount_range():
    points = T.validate({"FORWARD": 25.0, "ALIGN": -40.0, "NADIR": -89.0})
    assert T.output_for(30, points) == T.OUTPUT_MAX_DEG
    assert T.output_for(-120, points) == T.OUTPUT_MIN_DEG


# ---------------------------------------------------------------- camera_ctrl
def camera(tmp_path, **params):
    overrides = [Parameter("calibration_file", Parameter.Type.STRING, str(tmp_path / "camera_tilt.json")),
                 Parameter("startup_pose", Parameter.Type.STRING, "")]
    overrides += [Parameter(k, value=v) for k, v in params.items()]
    node = CameraCtrl(parameter_overrides=overrides)
    node.sent = []
    node.pub_cmd.publish = lambda m: node.sent.append(math.degrees(m.data))
    node.pub_state.publish = lambda m: setattr(node, "state_json", json.loads(m.data))
    node.applied = []
    node.pub_cal_applied.publish = lambda m: node.applied.append(json.loads(m.data))
    return node


def test_a_saved_calibration_is_loaded_and_every_pose_goes_out_through_it(tmp_path):
    (tmp_path / "camera_tilt.json").write_text(json.dumps({"points": MEASURED}))
    node = camera(tmp_path)
    try:
        node.request("NADIR")
        assert node.sent[-1] == pytest.approx(-78.0)
        node.request("BANNER")
        assert node.sent[-1] == pytest.approx(6 + (-38 - 6) * 20 / 45)
        node._tick()
        assert node.state_json["calibrated"] is True
        assert node.state_json["output"] == pytest.approx(node.sent[-1])
        assert node.state_json["output_unit"] == "deg"
    finally:
        node.destroy_node()


def test_a_jog_sends_the_raw_output_and_a_pose_request_returns_to_the_calibration(tmp_path):
    node = camera(tmp_path)
    try:
        node.request("NADIR")
        node._on_jog(String(data="-84.5"))
        assert node.sent[-1] == pytest.approx(-84.5)
        assert node.output() == pytest.approx(-84.5)
        node._on_jog(String(data="-120"))                  # past the mount
        assert node.sent[-1] == pytest.approx(T.OUTPUT_MIN_DEG)
        node.request("NADIR")                              # same pose again: sent again
        assert node.sent[-1] == pytest.approx(-90.0)
    finally:
        node.destroy_node()


def test_the_gcs_calibration_applies_at_once_and_survives_a_restart(tmp_path):
    node = camera(tmp_path)
    try:
        node.request("NADIR")
        node._on_calibration(String(data=json.dumps({"points": MEASURED})))
        assert node.sent[-1] == pytest.approx(-78.0), "the pose in force is re-sent"
        assert node.applied[-1]["points"] == MEASURED and node.applied[-1]["reason"] == ""
    finally:
        node.destroy_node()
    again = camera(tmp_path)
    try:
        again.request("NADIR")
        assert again.sent[-1] == pytest.approx(-78.0)
        again._on_calibration(String(data=json.dumps({"points": {"FORWARD": 0}})))
        assert "refused" in again.applied[-1]["reason"]
        assert again.calibration == MEASURED, "a refused calibration changes nothing"
        again._on_calibration(String(data=json.dumps({"points": None})))
        assert again.calibration is None and again.sent[-1] == pytest.approx(-90.0)
    finally:
        again.destroy_node()


def test_a_servo_mount_reading_its_output_back_settles_at_the_real_angle(tmp_path):
    # The FC reports the output it was sent; that output IS straight down.
    (tmp_path / "camera_tilt.json").write_text(json.dumps({"points": MEASURED}))
    node = camera(tmp_path, backend="mavlink", settle_hold_s=0.0)
    try:
        node.request("NADIR")
        half = math.radians(-78.0) / 2
        q = MagicMock(w=math.cos(half), x=0.0, y=math.sin(half), z=0.0)
        for _ in range(6):
            node._on_mount_status(MagicMock(q=q))
        assert math.degrees(node.actual_rad) == pytest.approx(-90.0)
        assert node.is_settled()
    finally:
        node.destroy_node()


# ------------------------------------------- camera_ctrl, the servo itself
# The aircraft (27 Oct 2026): no mount, the tilt servo on FC SERVO5, its pulse
# width set by the Pi with MAV_CMD_DO_SET_SERVO; the receiver's channel 6
# tilts it through the Pi when no mission runs.
SERVO_MEASURED = {"FORWARD": 1820.0, "ALIGN": 1490.0, "NADIR": 1120.0}


def servo_camera(tmp_path, **params):
    from test_winch import FakeCommandClient
    params.setdefault("rc_tilt_channel", 6)
    node = camera(tmp_path, backend="mavlink", fc_output="servo", **params)
    node.cli_cmd = FakeCommandClient()
    node.servo = lambda: [(int(r.param1), r.param2) for r, _ in node.cli_cmd.sent if r.command == 183]
    return node


def test_the_pi_sets_the_servo_pulse_on_output_5(tmp_path):
    node = servo_camera(tmp_path)
    try:
        for pose, pwm in (("FORWARD", 1500.0), ("ALIGN", 1250.0), ("NADIR", 1000.0)):
            node.request(pose)
            assert node.servo()[-1] == (5, pwm), pose
        assert not [r for r, _ in node.cli_cmd.sent if r.command == 205], "no mount command"
        node._tick()
        assert node.state_json["output_unit"] == "us"
        assert (node.state_json["output_min"], node.state_json["output_max"]) == (800.0, 2200.0)
    finally:
        node.destroy_node()


def test_a_microsecond_calibration_drives_the_servo_and_a_degree_one_is_refused(tmp_path):
    (tmp_path / "camera_tilt.json").write_text(json.dumps({"points": MEASURED}))
    node = servo_camera(tmp_path)
    try:
        node._load_calibration()                     # reported again, now captured
        assert node.calibration is None and "calibrate again" in node.applied[-1]["reason"]
        node._on_calibration(String(data=json.dumps({"points": SERVO_MEASURED})))
        assert node.applied[-1]["unit"] == "us" and node.applied[-1]["reason"] == ""
        node.request("NADIR")
        assert node.servo()[-1] == (5, 1120.0)
        node.request("BANNER")                       # -20 deg: between forward and 45 down
        assert node.servo()[-1][1] == pytest.approx(round(1820 + (1490 - 1820) * 20 / 45))
        node._on_jog(String(data="3000"))
        assert node.servo()[-1] == (5, 2200.0), "a jog stays inside servo_pwm_min..max"
    finally:
        node.destroy_node()
    saved = json.loads((tmp_path / "camera_tilt.json").read_text())
    assert saved["unit"] == "us" and saved["points"] == SERVO_MEASURED


def test_the_receiver_tilts_the_camera_when_no_mission_runs(tmp_path):
    node = servo_camera(tmp_path)
    try:
        node._on_rc(FakeRC(1500, 1700))
        node._tick()
        assert node.servo()[-1] == (5, 1700.0), "the receiver's channel 6 passed through"
        node.request("NADIR")                        # Camera cal or the mission
        assert node.servo()[-1] == (5, 1000.0)
        node._on_rc(FakeRC(1500, 1710))
        node._tick()
        assert node.servo()[-1] == (5, 1000.0), "a stick left where it was does not undo it"
        node._on_rc(FakeRC(1500, 1300))
        node._tick()
        assert node.servo()[-1] == (5, 1300.0), "moving the stick takes the camera back"
        node._on_mission_state(String(data="SEARCH_QR"))
        node._on_rc(FakeRC(1500, 1900))
        node._tick()
        assert node.servo()[-1] == (5, 1300.0), "the receiver is ignored during a mission"
    finally:
        node.destroy_node()


def test_on_the_aircraft_channel_8_tilts_the_camera_and_channel_6_never_does(tmp_path):
    # Operator, 29 Oct 2026: channel 6 (the winch switch) tilted the camera too.
    class Channels:
        def __init__(self, ch6, ch8):
            self.channels = [1500, 1500, 1000, 1500, 1000, ch6, 1500, ch8]

    node = servo_camera(tmp_path, rc_tilt_channel=8)
    try:
        node._on_rc(Channels(1500, 1500))
        node._tick()
        start = len(node.servo())
        for ch6 in (988, 2011, 1500, 988):               # the winch switch, every position
            node._on_rc(Channels(ch6, 1500))
            node._tick()
        assert len(node.servo()) == start and all(pwm != 988.0 and pwm != 2011.0
                                                  for _, pwm in node.servo()), node.servo()
        for ch8 in (988, 2011, 1500):
            node._on_rc(Channels(1500, ch8))
            node._tick()
            assert node.servo()[-1] == (5, float(ch8)), ch8
    finally:
        node.destroy_node()


def test_a_stale_or_absent_receiver_moves_nothing(tmp_path):
    node = servo_camera(tmp_path)
    try:
        node._on_rc(FakeRC(1500, 1700))
        node._rc = (node._rc[0], node._now() - 5.0)
        node._tick()
        assert node.servo() == []
        node._on_rc(FakeRC(1500, 0))                 # failsafe / no signal
        node._tick()
        assert node.servo() == []
    finally:
        node.destroy_node()


def test_nudges_and_the_calibration_follow_the_servo_microseconds(aggregator):
    a = aggregator
    a._on_camera_pose(String(data=json.dumps({"output": 1500.0, "output_unit": "us",
                                              "output_min": 800.0, "output_max": 2200.0})))
    assert a._dispatch("camera_cal", {"action": "nudge", "delta": 50}) == ("accepted", "")
    assert sent(a.pub_camera_jog)[-1] == "1550.00"
    assert a._dispatch("camera_cal", {"action": "nudge", "delta": 400})[0] == "rejected"
    a.state["camera_cal"]["draft"] = dict(SERVO_MEASURED)
    assert a._dispatch("camera_cal", {"action": "apply"}) == ("accepted", "")
    assert sent(a.pub_camera_cal)[-1]["points"] == SERVO_MEASURED
    a.state["camera_cal"]["draft"] = {"FORWARD": 1500.0, "ALIGN": 1495.0, "NADIR": 1100.0}
    assert "same output" in a._dispatch("camera_cal", {"action": "apply"})[1]


def test_the_aircraft_venue_drives_servo_5_from_the_pi():
    import yaml
    config = os.path.join(ROOT, "src", "aerothon_mission", "mission_bringup", "config")
    camera_params = yaml.safe_load(open(os.path.join(config, "venue.yaml")))["camera_ctrl"]["ros__parameters"]
    assert camera_params["fc_output"] == "servo" and camera_params["servo_channel"] == 5
    # Operator, 29 Oct 2026: the Pi alone drives output 5, channel 8 tilts the
    # camera through it, and channel 6 drives the winch alone. Passing channel 6
    # tilted the camera with the winch's switch; SERVO5_FUNCTION 58 (channel 8
    # on the FC) took the servo back from the Pi.
    assert camera_params["rc_tilt_channel"] == 8
    winch = yaml.safe_load(open(os.path.join(config, "venue.yaml")))["winch_ctrl"]["ros__parameters"]
    assert winch["rc_manual_channel"] == 6 != camera_params["rc_tilt_channel"]
    parm = open(os.path.join(config, "aerothon_hardware.parm"), encoding="utf-8").read()
    assert "\nSERVO5_FUNCTION 0\n" in parm and "\nMNT1_TYPE 0\n" in parm
    wiring = yaml.safe_load(open(os.path.join(config, "hardware_wiring.yaml")))
    assert wiring["camera_tilt"]["servo_function"] == 0
    sim_venue = yaml.safe_load(open(os.path.join(ROOT, "src", "aerothon_sim", "sim_gazebo", "config",
                                                 "world_sim_venue.yaml")))
    assert sim_venue["camera_ctrl"]["ros__parameters"]["fc_output"] == "mount", \
        "the simulator keeps its SITL mount"


# ---------------------------------------------------------------- winch_ctrl
class Winch:
    """An L298N winch with lowering on IN1 (FORWARD) and RC6 hand drive."""

    def __init__(self, tmp_path, **params):
        overrides = [Parameter("backend", Parameter.Type.STRING, "l298n"),
                     Parameter("payout_rate_mps", Parameter.Type.DOUBLE, 0.30),
                     Parameter("stow_rate_mps", Parameter.Type.DOUBLE, 0.45),
                     Parameter("max_payout_m", Parameter.Type.DOUBLE, 6.0),
                     Parameter("rc_manual_channel", Parameter.Type.INTEGER, 6),
                     Parameter("limits_file", Parameter.Type.STRING, str(tmp_path / "winch_limits.json"))]
        overrides += [Parameter(k, value=v) for k, v in params.items()]
        self.node = WinchNode(parameter_overrides=overrides)
        self.node.pub_status.publish = lambda m: setattr(self, "status", json.loads(m.data))
        self.node.motor = L298NDriver(0, 18, 23, 24, lg=FakeLgpio())
        self.node.fault, self.node.state = "", "IDLE"   # no lgpio on the test host
        self.rc(1500)
        self.tick()

    def tick(self, dt=0.5, n=1):
        for _ in range(n):
            self.node.integrate(dt)
            self.node._sync_l298n(dt)

    def rc(self, us):
        self.node._on_rc(FakeRC(1500, us))

    def run(self, us, seconds):
        self.rc(us)
        self.tick(0.5, int(round(seconds / 0.5)))
        self.rc(1500)
        self.tick()

    def cal(self, action, **kw):
        return self.node.calibrate(action, kw.get("length_m"))


@pytest.fixture
def winch(tmp_path):
    w = Winch(tmp_path)
    yield w
    w.node.destroy_node()


def calibrate(w, wind_in_s=3.0, pay_out_s=10.0, length=2.5):
    assert w.cal("begin") == ""
    w.run(1000, wind_in_s)                 # past the boot "wound up": limits lifted
    assert w.cal("set_min") == ""
    w.run(2000, pay_out_s)
    assert w.cal("set_max", length_m=length) == ""
    assert w.cal("end") == ""


def test_the_marks_become_the_limits_and_give_the_line_speed(winch, tmp_path):
    calibrate(winch)
    limit = winch.node.limit
    assert limit["max_payout_m"] == 2.5 and limit["stroke_s"] == pytest.approx(10.0)
    assert limit["line_speed_mps"] == pytest.approx(0.25)
    assert winch.node.payout == pytest.approx(2.5)
    saved = json.loads((tmp_path / "winch_limits.json").read_text())
    assert saved["limit"]["max_payout_m"] == 2.5 and saved["position_m"] == pytest.approx(2.5)


def test_rc6_hand_drive_stops_at_both_calibrated_limits(winch):
    calibrate(winch)
    winch.rc(2000)                                  # already paid out: nothing more
    winch.tick()
    assert winch.node.motor.direction == STOP
    winch.rc(1000)
    winch.tick(0.5, 4)
    assert winch.node.motor.direction == REVERSE    # winding in moves
    assert winch.node.payout == pytest.approx(2.5 - 0.25 * 2.0)
    winch.tick(0.5, 30)                              # 10 s back to the wound-up mark
    assert winch.node.payout == 0.0
    assert winch.node.motor.direction == STOP, "stopped at the wound-up limit"


def test_the_mission_lower_and_stow_run_between_the_limits_at_one_speed(winch):
    calibrate(winch)
    winch.run(1000, 10.0)
    assert winch.node.payout == 0.0
    winch.node._on_cmd(String(data="lower"))
    winch.tick(0.5, 19)                              # 9.5 s of the 10 s stroke
    assert winch.node.state == "LOWERING"
    winch.tick(0.5, 2)
    assert winch.node.state == "AT_LIMIT" and winch.node.motor.direction == STOP
    winch.node.publish_status()
    assert winch.status["limit_m"] == 2.5 and winch.status["limits"]["stroke_s"] == pytest.approx(10.0)
    winch.node._on_cmd(String(data="stow"))
    winch.tick(0.5, 19)
    assert winch.node.state == "STOWING", "the stow takes the whole stroke back"
    winch.tick(0.5, 2)
    assert winch.node.state == "IDLE" and winch.node.motor.direction == STOP


def test_uncalibrated_the_l298n_stows_at_its_lowering_speed(winch):
    # One motor at one duty: stowing at the faster stow_rate_mps estimate
    # stopped the motor with a third of the line still out.
    winch.node._on_cmd(String(data="lower"))
    winch.tick(0.5, 10)                              # 5 s at 0.30 m/s
    winch.node._on_cmd(String(data="stop"))
    assert winch.node.payout == pytest.approx(1.5)
    winch.node._on_cmd(String(data="stow"))
    winch.tick(0.5, 9)
    assert winch.node.state == "STOWING"
    winch.tick(0.5, 1)
    assert winch.node.state == "IDLE"


def test_uncalibrated_hand_drive_is_not_limited(winch):
    winch.run(1000, 2.0)                             # winding in from the boot zero
    assert winch.node.motor.direction == STOP
    winch.rc(1000)
    winch.tick()
    assert winch.node.motor.direction == REVERSE


def test_calibration_steps_are_refused_out_of_order_and_in_flight(winch):
    assert "start a calibration" in winch.cal("set_min")
    assert winch.cal("begin") == ""
    assert "wound-up limit first" in winch.cal("set_max", length_m=2.0)
    assert winch.cal("set_min") == ""
    assert "pay the line out" in winch.cal("set_max", length_m=2.0)
    winch.run(2000, 4.0)
    assert "measured" in winch.cal("set_max")
    assert "cannot deliver" in winch.cal("set_max", length_m=1.0)
    winch.node._on_mission_state(String(data="SEARCH_QR"))
    winch.tick()
    assert not winch.node.calibrating(), "a mission closes the calibration"
    assert winch.node.cal_reason == "a mission started"
    assert "mission is running" in winch.cal("begin")
    assert winch.node.limit is None


def test_a_restart_keeps_the_limits_and_where_the_line_is(tmp_path):
    w = Winch(tmp_path)
    calibrate(w)
    w.run(1000, 4.0)                                 # 1.0 m wound back in
    w.node.destroy_node()
    again = Winch(tmp_path)
    try:
        assert again.node.limit["max_payout_m"] == 2.5
        assert again.node.payout == pytest.approx(1.5)
        assert again.node.limit_source.startswith("saved calibration")
    finally:
        again.node.destroy_node()


def test_other_backends_refuse_the_calibration(tmp_path):
    node = WinchNode(parameter_overrides=[Parameter("backend", Parameter.Type.STRING, "gazebo")])
    try:
        assert "L298N backend" in node.calibrate("begin")
    finally:
        node.destroy_node()


# ---------------------------------------------------------------- mission
def test_the_release_is_made_from_no_higher_than_the_calibrated_line():
    from mission_bt.mission_tree import WinchDrop
    mav = MagicMock(winch_status={})
    drop = WinchDrop(mav, winch_reach_m=5.5)
    assert drop.reach() == 5.5
    mav.winch_status = {"limits": {"max_payout_m": 3.0}}
    assert drop.reach() == pytest.approx(2.5)
    mav.winch_status = {"limits": {"max_payout_m": 7.0}}
    assert drop.reach() == 5.5, "a longer line does not raise the venue reach"


# ---------------------------------------------------------------- aggregator
@pytest.fixture
def aggregator(tmp_path):
    with patch('rclpy.node.Node.__init__', return_value=None), \
         patch('rclpy.node.Node.create_subscription'), \
         patch('rclpy.node.Node.create_publisher'), \
         patch('rclpy.node.Node.create_client'), \
         patch('rclpy.node.Node.create_timer'), \
         patch('rclpy.node.Node.declare_parameter'), \
         patch('rclpy.node.Node.get_parameter',
               return_value=MagicMock(value=str(tmp_path / 'presets.json'))), \
         patch('rclpy.node.Node.get_logger'):
        from gcs_aggregator.aggregator import Aggregator
        node = Aggregator()
    for name in ("pub_camera_pose", "pub_camera_jog", "pub_camera_cal", "pub_winch_cal"):
        setattr(node, name, MagicMock())
    node.state["mission"]["armed"] = False
    return node


def camera_output(agg, deg):
    agg._on_camera_pose(String(data=json.dumps({"output": deg, "requested": "NADIR"})))


def sent(publisher):
    return [json.loads(c.args[0].data) if c.args[0].data.startswith("{") else c.args[0].data
            for c in publisher.publish.call_args_list]


def test_send_nudge_mark_and_apply_a_camera_calibration(aggregator):
    a = aggregator
    assert a._dispatch("camera_cal", {"action": "pose", "pose": "NADIR"}) == ("accepted", "")
    assert sent(a.pub_camera_pose) == ["NADIR"]
    camera_output(a, -90.0)
    assert a._dispatch("camera_cal", {"action": "nudge", "delta_deg": 5}) == ("accepted", "")
    assert a._dispatch("camera_cal", {"action": "nudge", "delta_deg": 5}) == ("accepted", "")
    assert sent(a.pub_camera_jog) == ["-85.00", "-80.00"], "two quick nudges add up"
    camera_output(a, -85.0)
    assert a._dispatch("camera_cal", {"action": "mark", "pose": "NADIR"})[0] == "rejected", \
        "the second nudge has not reached the camera"
    camera_output(a, -80.0)
    assert a._dispatch("camera_cal", {"action": "mark", "pose": "NADIR"}) == ("accepted", "")
    assert a._dispatch("camera_cal", {"action": "apply"}) == ("rejected", "no output recorded for FORWARD")
    for pose, output in (("ALIGN", -38.0), ("FORWARD", 6.0)):
        a._dispatch("camera_cal", {"action": "pose", "pose": pose})
        camera_output(a, output)
        assert a._dispatch("camera_cal", {"action": "mark", "pose": pose}) == ("accepted", "")
    assert a.state["camera_cal"]["draft"] == {"NADIR": -80.0, "ALIGN": -38.0, "FORWARD": 6.0}
    assert a._dispatch("camera_cal", {"action": "apply"}) == ("accepted", "")
    assert sent(a.pub_camera_cal)[-1]["points"] == {"NADIR": -80.0, "ALIGN": -38.0, "FORWARD": 6.0}


def test_calibrations_are_refused_in_the_air(aggregator):
    aggregator.state["mission"]["armed"] = True
    assert aggregator._dispatch("camera_cal", {"action": "pose", "pose": "NADIR"})[0] == "rejected"
    assert aggregator._dispatch("winch_cal", {"action": "begin"})[0] == "rejected"
    assert aggregator._dispatch("winch_cal", {"action": "end"})[0] == "accepted"


def test_winch_calibration_steps_are_forwarded_with_the_measured_line(aggregator):
    a = aggregator
    assert a._dispatch("winch_cal", {"action": "set_max"})[0] == "rejected"
    assert a._dispatch("winch_cal", {"action": "set_max", "length_m": 2.5})[0] == "accepted"
    assert a._dispatch("winch_cal", {"action": "lower"})[0] == "rejected"
    assert sent(a.pub_winch_cal) == [{"action": "set_max", "length_m": 2.5}]


# ---------------------------------------------------------------- wiring
def test_the_web_host_and_launch_carry_both_calibrations():
    web = open(os.path.join(ROOT, "src/aerothon_runtime/aerothon_runtime/web.py"), encoding="utf-8").read()
    assert "'camera_cal'" in web and "'winch_cal'" in web
    launch = open(os.path.join(ROOT, "src/aerothon_mission/mission_bringup/launch/mission2.launch.py"),
                  encoding="utf-8").read()
    assert "'calibration_file': os.path.join(measured_state, 'camera_tilt.json')" in launch
    assert "'limits_file': os.path.join(measured_state, 'winch_limits.json')" in launch


def test_a_calibration_window_confirms_its_reviewed_commands_over_itself():
    """Aircraft, 28 Oct 2026: Apply closed Camera cal and waited for Confirm in
    the Mission panel; the operator never saw it, so no calibration left the
    GCS and the poses kept their uncalibrated outputs. The window now stays
    open and the confirmation, labelled with what it applies, opens over it."""
    src = os.path.join(ROOT, "src/aerothon_gcs/tauri_app/src")
    app = open(os.path.join(src, "App.tsx"), encoding="utf-8").read()
    review = app[app.index("const reviewedSend"):app.index("const closeOverlay")]
    assert "Open(false)" not in review, "a reviewed command must not close its window"
    assert "{overlayOpen && review && (" in app and "{reviewBox}" in app
    assert "{!overlayOpen && reviewBox}" in app
    assert "{overlayOpen && outcome &&" in app, "command results show over every window"
    for name in ("CameraCalibration.tsx", "LidarCalibration.tsx",
                 "WinchCalibration.tsx", "ArenaDimensions.tsx"):
        text = open(os.path.join(src, name), encoding="utf-8").read()
        reviewed = [line for line in text.splitlines() if "true)" in line and "send(" in line]
        assert not reviewed, f"{name}: a reviewed command without a label: {reviewed}"
    camera = open(os.path.join(src, "CameraCalibration.tsx"), encoding="utf-8").read()
    assert "Apply camera calibration: forward ${show(draft.FORWARD)}" in camera
