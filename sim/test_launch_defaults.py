"""mission2.launch.py's hardware-facing defaults follow use_sim.

With fixed defaults, `use_sim:=false` alone drove the Gazebo winch joint and
camera joint while the aircraft's winch and tilt servo got nothing, and
started SLAM and RViz on the Pi.
"""

import importlib.util
import unittest
from pathlib import Path

LAUNCH = (Path(__file__).resolve().parent.parent
          / "src/aerothon_mission/mission_bringup/launch/mission2.launch.py")

try:
    from launch import LaunchContext
    from launch.actions import DeclareLaunchArgument
    from launch.utilities import perform_substitutions
except ImportError:                                   # no ROS on this host
    LaunchContext = None


def defaults(use_sim):
    spec = importlib.util.spec_from_file_location("mission2_launch", LAUNCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        ld = mod.generate_launch_description()
    except Exception as e:                            # noqa: BLE001
        raise unittest.SkipTest(f"workspace not built/sourced: {e}")
    ctx = LaunchContext()
    ctx.launch_configurations["use_sim"] = use_sim
    return {a.name: perform_substitutions(ctx, a.default_value)
            for a in ld.entities if isinstance(a, DeclareLaunchArgument)
            and a.name in ("rviz", "slam", "winch_backend", "camera_backend")}


@unittest.skipIf(LaunchContext is None, "ROS 2 launch not installed")
class LaunchDefaultsTests(unittest.TestCase):

    def test_the_aircraft_drives_real_hardware_and_skips_the_desktop(self):
        self.assertEqual(defaults("false"), {
            "rviz": "false", "slam": "false",
            "winch_backend": "mavlink", "camera_backend": "mavlink"})

    def test_the_simulator_keeps_its_backends(self):
        self.assertEqual(defaults("true"), {
            "rviz": "true", "slam": "true",
            "winch_backend": "gazebo", "camera_backend": "sim"})


if __name__ == "__main__":
    unittest.main()
