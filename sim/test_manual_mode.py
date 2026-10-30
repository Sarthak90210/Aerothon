"""The GCS's manual-flight mode (profile mode "manual", launch manual:=true).

The transmitter flies. The Pi runs MAVROS, the stream rates (RC channels),
rc_in_bridge, the camera servo, the winch, the GCS aggregator and the raw
webcam feed, and nothing that detects, maps, scans or flies: no perception,
lidar, SLAM, avoidance, mission executive or execution service. The router is a host service and runs
in every mode.
"""

import asyncio
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "aerothon_runtime"))
LAUNCH = ROOT / "src/aerothon_mission/mission_bringup/launch/mission2.launch.py"

from aerothon_runtime.contracts import profile  # noqa: E402

try:
    from launch import LaunchContext
    from launch.actions import DeclareLaunchArgument, TimerAction
    from launch.utilities import perform_substitutions
    from launch_ros.actions import Node
except ImportError:                                   # no ROS on this host
    LaunchContext = None

try:
    from aerothon_runtime import web
except ImportError:                                   # no aiohttp on this host
    web = None

MANUAL_NODES = {
    ("mavros", "mavros_node"),
    ("mission_bringup", "stream_rate_keeper"),
    ("aerothon_runtime", "rc_in_bridge"),
    ("camera_ctrl", "camera_ctrl_node"),
    ("winch_ctrl", "winch_node"),
    ("gcs_aggregator", "aggregator"),
    ("web_video_server", "web_video_server"),
}
# On the aircraft the Pi's own webcam feeds the GCS video (no detector reads it).
WEBCAM = {("usb_cam", "usb_cam_node_exe"), ("mission_bringup", "camera_exposure")}

DRONE = {"id": "vehicle", "transport": "serial", "device": "/dev/ttyAMA2",
         "vehicle": "drone", "winch_backend": "l298n", "slam": True}


class ProfileModeTests(unittest.TestCase):

    def test_profiles_default_to_the_full_mission_stack(self):
        self.assertEqual(profile(dict(DRONE))["mode"], "mission")

    def test_manual_is_accepted_and_anything_else_refused(self):
        self.assertEqual(profile(dict(DRONE, mode="manual"))["mode"], "manual")
        with self.assertRaises(ValueError):
            profile(dict(DRONE, mode="autonomous"))


def started_nodes(**overrides):
    """(package, executable) of every node the launch would start."""
    spec = importlib.util.spec_from_file_location("mission2_launch_manual", LAUNCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        ld = mod.generate_launch_description()
    except Exception as e:                            # noqa: BLE001
        raise unittest.SkipTest(f"workspace not built/sourced: {e}")
    ctx = LaunchContext()
    entities = list(ld.entities)
    for entity in entities:
        if isinstance(entity, DeclareLaunchArgument):
            ctx.launch_configurations[entity.name] = overrides.get(
                entity.name, perform_substitutions(ctx, entity.default_value))
    nodes = []
    for entity in entities:
        actions = entity.actions if isinstance(entity, TimerAction) else [entity]
        for action in actions:
            if isinstance(action, Node) and (
                    action.condition is None or action.condition.evaluate(ctx)):
                nodes.append((action.node_package, action.node_executable))
    return set(nodes)


@unittest.skipIf(LaunchContext is None, "ROS 2 launch not installed")
class ManualLaunchTests(unittest.TestCase):
    AIRCRAFT = dict(use_sim="false", managed="true", slam="true", rviz="true")

    def test_manual_starts_only_the_servo_winch_and_gcs(self):
        self.assertEqual(started_nodes(**self.AIRCRAFT, manual="true"), MANUAL_NODES | WEBCAM)

    def test_mission_mode_keeps_the_full_stack(self):
        nodes = started_nodes(**self.AIRCRAFT, manual="false")
        self.assertTrue(MANUAL_NODES | WEBCAM <= nodes)
        for wanted in [("perception_qr", "qr_node"), ("sllidar_ros2", "sllidar_node"),
                       ("aerothon_runtime", "execution_node"), ("slam_toolbox", "async_slam_toolbox_node"),
                       ("usb_cam", "usb_cam_node_exe"), ("avoidance", "velocity_controller")]:
            self.assertIn(wanted, nodes)

    def test_a_simulated_manual_run_keeps_its_device_gateway(self):
        nodes = started_nodes(use_sim="true", managed="true", manual="true",
                              remote_gateway="http://127.0.0.1:8090")
        self.assertEqual(nodes, MANUAL_NODES | {("aerothon_runtime", "remote_devices")})


@unittest.skipIf(web is None, "aiohttp not installed")
class WebHostManualTests(unittest.TestCase):

    def host(self, mode):
        state = tempfile.TemporaryDirectory()
        self.addCleanup(state.cleanup)
        h = web.Host(state.name, state.name)
        p = profile(dict(DRONE, mode=mode))
        h.profiles[p["id"]] = p
        h.profile_id = p["id"]
        return h, p

    def launch_args(self, mode):
        h, p = self.host(mode)
        with patch.object(web.asyncio, "create_subprocess_exec", AsyncMock()) as run, \
                patch.dict(os.environ, {"AEROTHON_DEVICE_STATE_DIR": tempfile.mkdtemp()}):
            asyncio.run(h.launch_runtime(p))
        return run.call_args.args

    def test_manual_launches_manual_with_slam_off(self):
        args = self.launch_args("manual")
        self.assertIn("manual:=true", args)
        self.assertIn("slam:=false", args)

    def test_mission_launch_keeps_the_profiles_slam(self):
        args = self.launch_args("mission")
        self.assertIn("manual:=false", args)
        self.assertIn("slam:=true", args)

    def test_manual_refuses_a_task_start_and_says_why(self):
        h, _ = self.host("manual")
        h.internal_ws = MagicMock()
        h.telemetry = {"safety": {"fcu_connected": True}, "sample_age_s": {"state": 0.1},
                       "runtime_health": {"fresh": True}}
        h.received = time.monotonic()
        with self.assertRaisesRegex(ValueError, "manual mode runs no missions"):
            asyncio.run(h.command({"command_id": "manual-start-1", "cmd": "start",
                                   "args": {"task": "mechanism", "params": {"action": "stow"}}}))
        self.assertEqual(h.state()["mode"], "manual")


if __name__ == "__main__":
    unittest.main()
