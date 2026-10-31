"""The world-maker simulation's venue file: venue.yaml plus measured sim values.

The laptop simulation flies the corridor at 1.0 m/s (velocity_controller
cruise_speed) and paces the search with the simulated airframe's MEASURED
stop (search_brake_mps2, logs/return_lap_20261020/brake_probe). Everything
else must stay the aircraft's venue.yaml, or the simulation stops testing it.
"""

import math
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VENUE = ROOT / "src/aerothon_mission/mission_bringup/config/venue.yaml"
SIM_VENUE = ROOT / "src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml"
LAUNCH = ROOT / "src/aerothon_mission/mission_bringup/launch/mission2.launch.py"
SIM_ONLY = {("mission_bt", "crossing_strip_m"),
            ("mission_bt", "search_speed_override_mps"),
            ("velocity_controller", "cruise_speed"),
            ("velocity_controller", "passage_half_width"),
            ("velocity_controller", "clearance_floor_m")}
# Aircraft values the simulation must replace: its SITL flight controller has a
# camera mount on the Gazebo joint (the aircraft's Pi drives SERVO5 itself,
# 27 Oct 2026), and it has no receiver to pass through (the aircraft's channel
# 8 tilts the camera, 29 Oct). The search braking: the aircraft's 1.0 is an
# unmeasured competition-day choice (31 Oct), the simulation's 0.8 measured.
SIM_REPLACES = {("camera_ctrl", "fc_output"): "mount", ("camera_ctrl", "rc_tilt_channel"): 0,
                ("mission_bt", "search_brake_mps2"): 0.8}


def params(path):
    data = yaml.safe_load(path.read_text())
    return {(node, key): value for node, body in data.items()
            for key, value in body["ros__parameters"].items()}


class WorldSimVenueTests(unittest.TestCase):

    def test_only_the_measured_sim_values_differ_from_the_aircraft_venue(self):
        aircraft, sim = params(VENUE), params(SIM_VENUE)
        self.assertEqual({k: sim[k] for k in SIM_REPLACES}, SIM_REPLACES)
        self.assertEqual({k: v for k, v in sim.items() if k not in SIM_ONLY | set(SIM_REPLACES)},
                         {k: v for k, v in aircraft.items() if k not in SIM_REPLACES})
        self.assertEqual(set(sim) - set(aircraft), SIM_ONLY)

    def test_sim_values_are_floats_in_range(self):
        sim = params(SIM_VENUE)
        cruise = sim[("velocity_controller", "cruise_speed")]
        brake = sim[("mission_bt", "search_brake_mps2")]
        self.assertIsInstance(cruise, float)          # ROS refuses an int here
        self.assertIsInstance(brake, float)
        self.assertEqual(cruise, 1.0)
        self.assertGreaterEqual(brake, 0.5)            # never below the default
        self.assertLessEqual(brake, 2.5)               # ArduPilot WPNAV_ACCEL default
        clearance = sim[("velocity_controller", "passage_half_width")]
        strip = sim[("mission_bt", "crossing_strip_m")]
        self.assertEqual(clearance, 0.45)              # the user's simulation choice
        self.assertAlmostEqual(strip, 2 * clearance)   # one clearance, both stages
        self.assertGreater(clearance, 0.4)             # never inside the airframe radius
        self.assertEqual(sim[("velocity_controller", "clearance_floor_m")], clearance)

    def test_the_velocity_controller_is_given_the_venue_file(self):
        text = LAUNCH.read_text()
        start = text.index("executable='velocity_controller'")
        self.assertIn("parameters=[params_file,", text[start:start + 300])

    def test_the_world_maker_profile_selects_it(self):
        text = (ROOT / "tools/world_editor/serve.py").read_text()
        self.assertIn('src/aerothon_sim/sim_gazebo/config/world_sim_venue.yaml', text)
        self.assertIn('"venue_file": str(SIM_VENUE) if SIM_VENUE.is_file() else ""', text)


def ray_scan(segments, n=721, a0=-math.pi / 2, inc=math.radians(0.25)):
    """A planar lidar scan of line segments ((x0, y0), (x1, y1)) from the origin."""
    ranges = []
    for k in range(n):
        a = a0 + k * inc
        dx, dy = math.cos(a), math.sin(a)
        best = float("inf")
        for (x0, y0), (x1, y1) in segments:
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t = (x0 * ey - y0 * ex) / den
            u = (x0 * dy - y0 * dx) / den
            if t > 0 and 0 <= u <= 1:
                best = min(best, t)
        ranges.append(best)
    return a0, inc, ranges


class ClearanceFloorTests(unittest.TestCase):
    """The planner's 0.70 m lock stays the default; a venue may lower it to 0.45 m."""

    def test_default_floor_still_refuses_less_than_0_70(self):
        from avoidance.local_planner import LocalPlanner
        with self.assertRaisesRegex(ValueError, "0.70 m"):
            LocalPlanner(0.45, occupied_radius=0.4)

    def test_a_simulation_floor_accepts_0_45_and_no_lower(self):
        from avoidance.local_planner import LocalPlanner
        self.assertEqual(LocalPlanner(0.45, occupied_radius=0.4, clearance_floor=0.45).clearance, 0.45)
        with self.assertRaises(ValueError):
            LocalPlanner(0.40, occupied_radius=0.4, clearance_floor=0.40)
        with self.assertRaises(ValueError):
            LocalPlanner(0.70, occupied_radius=0.4, clearance_floor=0.80)


class CrossingStripTests(unittest.TestCase):
    """DuckUnderBoard keeps the aircraft's 1.5 m strip unless the venue narrows it."""

    def test_default_strip_is_the_aircrafts(self):
        from types import SimpleNamespace
        from mission_bt.mission_tree import DuckUnderBoard
        self.assertEqual(DuckUnderBoard(SimpleNamespace()).crossing_strip_m, 1.5)
        self.assertEqual(DuckUnderBoard(SimpleNamespace(), crossing_strip_m=0.9).crossing_strip_m, 0.9)

    def test_the_shipped_gate_is_refused_at_1_5_and_open_at_0_9(self):
        """20 Oct, world 'shipped': posts 4.1 m apart at 4.87 m, a lane wall
        starting 0.8 m past them 0.74 m to the right of the flight line (2 m
        lane, aircraft 0.26 m off centre)."""
        from mission_bt.scan_geometry import gate_opening
        gate, post = 4.87, 0.06
        posts = [((gate, y - post), (gate, y + post)) for y in (2.05, -2.05)]
        walls = [((gate + 0.8, -0.74), (gate + 6.0, -0.74)),
                 ((gate + 0.8, 1.26), (gate + 6.0, 1.26))]
        a0, inc, ranges = ray_scan(posts + walls)
        kw = dict(need_clear_m=0.0, range_max=12.0)
        wide = gate_opening(a0, inc, ranges, 0.0, math.radians(35), **kw)
        narrow = gate_opening(a0, inc, ranges, 0.0, math.radians(35), corridor_m=0.9, **kw)
        self.assertLess(wide["clear_m"], gate + 1.0, wide)        # refused: < gate + 1.0 m
        self.assertGreaterEqual(narrow["clear_m"], gate + 1.0, narrow)


if __name__ == "__main__":
    unittest.main()

