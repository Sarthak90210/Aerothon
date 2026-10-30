#!/usr/bin/env python3
"""The organisers' six fence points and the optional course points (31 Oct 2026).

The operator asked for the GCS to take the aircraft to each point and record
it: the six fence points first (required), then home and the two corridors'
ends (optional; without them the mission finds everything as before). These
pin the recording (5 s of the aircraft's own GPS, refused without a good fix),
what Apply sends, the advisory home check, and what the mission does with the
course points: face the entry corridor before the banner search, refuse a gate
they place in the exit lane, fly back to the recorded exit mouth and home --
each only when recorded, and only within a sanity distance of what the camera,
lidar and FC say.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_course_points.py -v
"""

import json
import math
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_mission", "mission_bt"))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_gcs", "gcs_aggregator"))
sys.path.insert(0, os.path.join(ROOT, "sim"))

import py_trees                                                    # noqa: E402

from gcs_aggregator import organiser_points as OP                  # noqa: E402
from gcs_aggregator.readiness import blocking_reasons, evaluate, is_ready  # noqa: E402
from mission_bt.delivery_zone import parse_course_points           # noqa: E402
from mission_bt.geofence import local_to_global                    # noqa: E402

HOME = (13.1705900, 77.5331760)
SURVEY = {
    "fence_back_left": local_to_global(-1.45, -23.94, *HOME),
    "fence_back_right": (13.1707773, 77.5332852),
    "zone_1": (13.1705131, 77.5330233), "zone_2": (13.1707149, 77.5330967),
    "zone_3": (13.1707636, 77.5329365), "zone_4": (13.1705581, 77.5328695),
}
OK = py_trees.common.Status.SUCCESS
RUNNING = py_trees.common.Status.RUNNING
FAILURE = py_trees.common.Status.FAILURE


def stored(points):
    return {k: OP.typed(*v) for k, v in points.items()}


class RecorderTests(unittest.TestCase):

    def feed(self, rec, n, lat=HOME[0], lon=HOME[1], sats=14, fix=True, jitter=0.0):
        for i in range(n):
            rec.add(lat + jitter * (i % 2), lon, fix, sats)

    def test_five_seconds_of_fixes_average_to_the_spot(self):
        rec = OP.Recorder("home", 100.0)
        self.feed(rec, 25, jitter=2e-6)            # ~0.2 m apart
        self.assertIsNone(rec.poll(103.0))         # still recording
        point, why = rec.poll(105.1)
        self.assertEqual(why, "")
        self.assertEqual(point["source"], "recorded")
        self.assertEqual(point["samples"], 25)
        self.assertAlmostEqual(point["lat"], HOME[0] + 1e-6, places=7)
        self.assertLess(point["spread_m"], 0.3)

    def test_a_lost_fix_or_few_satellites_is_refused(self):
        rec = OP.Recorder("home", 0.0)
        self.feed(rec, 5)
        rec.add(HOME[0], HOME[1], False, 14)
        self.assertIn("fix was lost", rec.poll(6.0)[1])
        rec = OP.Recorder("home", 0.0)
        self.feed(rec, 5, sats=6)
        self.assertIn("satellites", rec.poll(6.0)[1])

    def test_a_moving_aircraft_or_too_few_fixes_is_refused(self):
        rec = OP.Recorder("zone_1", 0.0)
        self.feed(rec, 20, jitter=5e-5)            # 5.5 m apart
        self.assertIn("spread", rec.poll(6.0)[1])
        rec = OP.Recorder("zone_1", 0.0)
        self.feed(rec, 3)
        self.assertIn("only 3", rec.poll(6.0)[1])

    def test_mavros_unset_zero_is_not_a_fix(self):
        rec = OP.Recorder("home", 0.0)
        for _ in range(10):
            rec.add(0.0, 0.0, True, 14)
        self.assertIn("only 0", rec.poll(6.0)[1])


class BoundaryTests(unittest.TestCase):

    def test_the_six_fence_points_are_required_first(self):
        fence, zone, course, why = OP.boundaries(stored({"zone_1": SURVEY["zone_1"]}))
        self.assertIsNone(fence)
        self.assertIn("behind take-off, left", why)
        self.assertEqual([k for k, _, required in OP.SLOTS if required],
                         list(OP.FENCE_KEYS + OP.ZONE_KEYS))
        self.assertEqual([k for k, _, _ in OP.SLOTS[:6]], list(OP.FENCE_KEYS + OP.ZONE_KEYS))

    def test_fence_is_the_outline_and_the_zone_its_four_corners(self):
        fence, zone, course, why = OP.boundaries(stored(SURVEY))
        self.assertEqual(why, "")
        self.assertEqual(len(fence), 4)            # near corners fall inside
        got = {(round(p["lat"], 7), round(p["lon"], 7)) for p in fence}
        for key in ("fence_back_left", "fence_back_right", "zone_3", "zone_4"):
            self.assertIn(tuple(round(v, 7) for v in SURVEY[key]), got)
        self.assertEqual([(p["lat"], p["lon"]) for p in zone],
                         [SURVEY[k] for k in OP.ZONE_KEYS])
        self.assertEqual(course, {"home": None, "entry": None, "exit": None})

    def test_course_points_are_optional_and_a_corridor_needs_both_ends(self):
        pts = dict(SURVEY, home=HOME, entry_home=local_to_global(-5.7, 1.3, *HOME),
                   exit_zone=local_to_global(-11.0, -4.4, *HOME))
        _, _, course, _ = OP.boundaries(stored(pts))
        self.assertIsNotNone(course["home"])
        self.assertIsNone(course["entry"])         # one end only
        self.assertIsNone(course["exit"])
        pts["entry_zone"] = local_to_global(-12.0, 1.3, *HOME)
        _, _, course, _ = OP.boundaries(stored(pts))
        self.assertEqual(len(course["entry"]), 2)
        parsed, why = parse_course_points(json.dumps(course))
        self.assertEqual(why, "")
        self.assertEqual(parsed["entry"][0], (pts["entry_home"][0], pts["entry_home"][1]))

    def test_points_survive_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "points.json")
            OP.save(path, dict(stored(SURVEY), bogus={"lat": 1, "lon": 2},
                               home={"lat": "x", "lon": 2}))
            back = OP.load(path)
            self.assertEqual(set(back), set(SURVEY))


class AggregatorTests(unittest.TestCase):
    """record_point / set_point / apply_organiser_points on the aggregator,
    called on a stand-in for the node."""

    def setUp(self):
        import time
        from gcs_aggregator.aggregator import Aggregator
        self.A = Aggregator
        self.tmp = tempfile.TemporaryDirectory()
        self.sent = []
        pub = lambda topic: NS(publish=lambda m: self.sent.append((topic, m.data)))  # noqa: E731
        self.node = NS(
            state={"mission": {"armed": False},
                   "gps": {"lat": HOME[0], "lon": HOME[1], "sats": 14, "fix": "3D"},
                   "organiser_points": {"slots": [], "points": {}, "recording": None,
                                        "last": None, "applied": None}},
            _steady_seen={"gps": time.monotonic()}, _recorder=None,
            _points_path=os.path.join(self.tmp.name, "points.json"),
            pub_geofence=pub("geofence"), pub_delivery_zone=pub("zone"),
            pub_course_points=pub("course"))

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, cmd, **args):
        return self.A._points_command(self.node, cmd, args)

    def test_apply_needs_the_six_then_sends_fence_zone_and_course(self):
        self.assertEqual(self.cmd("apply_organiser_points")[0], "rejected")
        for key, (lat, lon) in SURVEY.items():
            self.assertEqual(self.cmd("set_point", slot=key, lat=lat, lon=lon)[0], "accepted")
        self.assertEqual(self.cmd("apply_organiser_points"), ("accepted", ""))
        topics = dict(self.sent)
        self.assertEqual(len(json.loads(topics["geofence"])["vertices"]), 4)
        self.assertEqual(len(json.loads(topics["zone"])["vertices"]), 4)
        self.assertEqual(json.loads(topics["course"]),
                         {"home": None, "entry": None, "exit": None})
        self.assertEqual(set(OP.load(self.node._points_path)), set(SURVEY))

    def test_points_change_only_disarmed_but_recording_works_armed(self):
        self.node.state["mission"]["armed"] = True
        self.assertEqual(self.cmd("set_point", slot="home", lat=HOME[0], lon=HOME[1])[0],
                         "rejected")
        self.assertEqual(self.cmd("record_point", slot="home")[0], "accepted")
        self.assertEqual(self.cmd("record_point", slot="zone_1")[0], "rejected")

    def test_recording_needs_a_fresh_good_fix(self):
        self.node.state["gps"]["sats"] = 5
        self.assertIn("satellites", self.cmd("record_point", slot="home")[1])
        self.node.state["gps"]["sats"] = 14
        self.node._steady_seen["gps"] -= 10.0
        self.assertIn("fresh", self.cmd("record_point", slot="home")[1])
        self.assertEqual(self.cmd("record_point", slot="nowhere")[0], "rejected")

    def test_a_recording_lands_in_its_slot(self):
        self.assertEqual(self.cmd("record_point", slot="home")[0], "accepted")
        for _ in range(20):
            self.node._recorder.add(HOME[0], HOME[1], True, 14)
        self.node._recorder.t0 -= 6.0
        self.A._poll_recorder(self.node)
        op = self.node.state["organiser_points"]
        self.assertTrue(op["last"]["ok"])
        self.assertEqual(op["points"]["home"]["source"], "recorded")
        self.assertIsNone(self.node._recorder)


class ReadinessTests(unittest.TestCase):

    def test_the_home_check_warns_without_holding_the_interlock(self):
        base = evaluate({})
        self.assertNotIn("home_point", [i["key"] for i in base])
        items = [dict(i, ok=True) for i in evaluate({"home_point_m": 4.2})]
        home = [i for i in items if i["key"] == "home_point"][0]
        home["ok"] = 4.2 <= 2.0
        self.assertTrue(home["advisory"])
        self.assertTrue(is_ready(items))
        self.assertEqual(blocking_reasons(items), [])
        near = [i for i in evaluate({"home_point_m": 1.0}) if i["key"] == "home_point"][0]
        self.assertTrue(near["ok"])


def commander():
    from mission_bt.mav_commander import Mav
    mav = Mav.__new__(Mav)
    mav._logged = set()
    mav.node = NS(get_logger=lambda: NS(info=lambda *a: None))
    mav.home = NS(geo=NS(latitude=HOME[0], longitude=HOME[1]),
                  position=NS(x=0.0, y=0.0))
    mav.course_global = None
    return mav


class CommanderTests(unittest.TestCase):

    def test_course_points_resolve_about_home(self):
        mav = commander()
        course = {"home": {"lat": HOME[0], "lon": HOME[1]},
                  "entry": [dict(zip(("lat", "lon"), local_to_global(-5.7, 1.3, *HOME))),
                            dict(zip(("lat", "lon"), local_to_global(-11.9, 3.0, *HOME)))],
                  "exit": None}
        mav._on_course_points(NS(data=json.dumps(course)))
        self.assertAlmostEqual(mav.course_home_local[0], 0.0, places=3)
        (ex, ey), _ = mav.entry_corridor_local
        self.assertAlmostEqual(ex, -5.7, places=2)
        self.assertAlmostEqual(ey, 1.3, places=2)
        self.assertIsNone(mav.exit_corridor_local)

    def test_a_malformed_message_gives_no_guidance(self):
        mav = commander()
        mav._on_course_points(NS(data='{"entry": [{"lat": 1}]}'))
        self.assertIsNone(mav.entry_corridor_local)
        self.assertIsNone(parse_course_points("not json")[0])


class Fake:
    def __init__(self, pos=(0.0, 0.0, 5.0), yaw=0.0):
        self._pos, self._yaw = pos, yaw
        self.gotos, self.logs = [], []
        self.entry_corridor_local = None
        self.exit_corridor_local = None
        self.course_home_local = None
        self.banner_square_xy = None
        self.gate_rejected = False
        self.abort_reason = ""

    def pos(self):
        return self._pos

    def yaw(self):
        return self._yaw

    def goto(self, *a):
        self.gotos.append(a)

    def log(self, msg, warn=False):
        self.logs.append(msg)

    def home_local_xy(self):
        return (0.0, 0.0)


class FaceEntryCorridorTests(unittest.TestCase):

    def test_without_points_it_passes_at_once(self):
        from mission_bt.mission_tree import FaceEntryCorridor
        mav = Fake()
        leaf = FaceEntryCorridor("Face", mav)
        leaf.tick_once()
        self.assertEqual(leaf.status, OK)
        self.assertEqual(mav.gotos, [])

    def test_it_turns_in_place_to_the_entry_mouth(self):
        from mission_bt.mission_tree import FaceEntryCorridor
        mav = Fake(pos=(1.5, 0.0, 5.0), yaw=0.0)
        mav.entry_corridor_local = ((5.5, 4.0), (11.5, 4.0))
        leaf = FaceEntryCorridor("Face", mav)
        leaf.tick_once()
        self.assertEqual(leaf.status, RUNNING)
        x, y, z, yaw = mav.gotos[-1]
        self.assertEqual((x, y, z), (1.5, 0.0, 5.0))
        self.assertAlmostEqual(yaw, math.atan2(4.0, 4.0))
        mav._yaw = yaw
        leaf.tick_once()
        self.assertEqual(leaf.status, OK)


class CheckGateTests(unittest.TestCase):

    def setUp(self):
        self.mav = Fake()
        self.mav.entry_corridor_local = ((5.5, 2.75), (11.5, 2.75))
        self.mav.exit_corridor_local = ((11.5, -2.75), (5.5, -2.75))

    def check(self, gate, final=False):
        from mission_bt.mission_tree import CheckGateAgainstCourse
        self.mav.banner_square_xy = gate
        leaf = CheckGateAgainstCourse("Check", self.mav, final=final)
        leaf.tick_once()
        return leaf.status

    def test_the_entry_gate_passes_within_gps_error(self):
        self.assertEqual(self.check((6.5, 1.3)), OK)
        self.assertFalse(self.mav.gate_rejected)

    def test_the_exit_lane_gate_is_refused_then_fails_on_the_second_pass(self):
        self.assertEqual(self.check((5.6, -2.5)), FAILURE)
        self.assertTrue(self.mav.gate_rejected)
        self.assertEqual(self.mav.abort_reason, "")
        self.mav.gate_rejected = False
        self.assertEqual(self.check((5.6, -2.5), final=True), FAILURE)
        self.assertIn("second alignment", self.mav.abort_reason)

    def test_no_entry_points_means_no_check(self):
        self.mav.entry_corridor_local = None
        self.assertEqual(self.check((50.0, 50.0)), OK)

    def test_with_the_entry_lane_only_a_far_gate_is_refused(self):
        self.mav.exit_corridor_local = None
        self.assertEqual(self.check((7.0, 0.0)), OK)
        self.assertEqual(self.check((5.5, -3.0)), FAILURE)

    def test_only_a_refusal_runs_the_second_pass(self):
        from mission_bt.mission_tree import GateWasRejected
        leaf = GateWasRejected(self.mav)
        leaf.tick_once()
        self.assertEqual(leaf.status, FAILURE)
        self.mav.gate_rejected = True
        leaf.tick_once()
        self.assertEqual(leaf.status, OK)
        self.assertFalse(self.mav.gate_rejected)


class ReturnAndHomeTests(unittest.TestCase):

    def test_the_return_flies_to_a_recorded_mouth_near_the_derived_one(self):
        from mission_bt.mission_tree import ReturnToCorridorMouth
        mav = Fake()
        mav.gate_heading = 0.0
        leaf = ReturnToCorridorMouth(mav, lane_offset_m=-5.5)
        derived = leaf.return_mouth((11.5, 2.75, 1.2, 0.0))
        self.assertAlmostEqual(derived[1], -2.75)
        mav.exit_corridor_local = ((12.3, -3.6), (6.3, -3.6))
        rx, ry, tyaw = leaf.return_mouth((11.5, 2.75, 1.2, 0.0))
        self.assertEqual((rx, ry), (12.3, -3.6))
        self.assertAlmostEqual(tyaw, derived[2])   # the lidar axis is kept
        mav.exit_corridor_local = ((25.0, -3.0), (19.0, -3.0))
        leaf = ReturnToCorridorMouth(mav, lane_offset_m=-5.5)
        self.assertEqual(leaf.return_mouth((11.5, 2.75, 1.2, 0.0))[:2], derived[:2])

    def test_home_is_the_recorded_point_near_the_fcs(self):
        from mission_bt.mission_tree import GotoHome
        mav = Fake()
        leaf = GotoHome(mav, 5.0)
        self.assertEqual(leaf._home(), (0.0, 0.0))
        mav.course_home_local = (0.6, -0.4)
        self.assertEqual(leaf._home(), (0.6, -0.4))
        mav.course_home_local = (9.0, 0.0)
        self.assertEqual(leaf._home(), (0.0, 0.0))
        self.assertEqual(len(mav.logs), 1)


class CorridorExitTests(unittest.TestCase):

    def test_the_aircraft_is_told_to_hold_where_the_walls_end(self):
        # The venue world coasted 1.6 m at 0.8 m/s after the navigator was
        # switched off (31 Oct 2026, headless c04) and climbed over red.
        from mission_bt.mission_tree import Corridor
        from test_fail_closed_stages import FakeMav
        mav = FakeMav()
        mav._pos = (13.2, 2.7, 1.2)
        mav._alt = 1.2
        mav.exited = True
        leaf = Corridor("Corridor", mav, alt=1.2)
        leaf.tick_once()
        self.assertEqual(leaf.status, OK)
        self.assertEqual(mav.gotos[-1][:3], (13.2, 2.7, 1.2))


if __name__ == "__main__":
    unittest.main()
