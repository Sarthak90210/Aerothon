#!/usr/bin/env python3
"""The surveyed venue world (30 Oct 2026) and what the operator types for it.

scripts/venue_world.py builds sim/worlds/aerothon26_venue*.json from the
operator's GPS survey, turned to the corridors' 286.5 deg true heading. These
pin it to the survey, the operator's figures (lanes, boards, red pad, start
marker), the fence of the two back points and the zone corners, and the
organiser inputs and turned-zone publication the runs use.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_venue_world.py -v
"""

import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_mission", "mission_bt"))

import venue_world as V                                          # noqa: E402
import world_spec as W                                           # noqa: E402
from mission_bt import arena_dimensions as A                     # noqa: E402
from mission_bt.delivery_zone import boundary_to_local_polygon   # noqa: E402
from mission_bt.geofence import global_to_local                  # noqa: E402

HOME = (13.1705900, 77.5331760)
SURVEY_ZONE = [(13.1705131, 77.5330233), (13.1707149, 77.5330967),
               (13.1707636, 77.5329365), (13.1705581, 77.5328695)]
SURVEY_BACK_RIGHT = (13.1707773, 77.5332852)


class VenueWorldTests(unittest.TestCase):

    def setUp(self):
        self.spec = V.build("venue_test")

    def test_it_validates_with_the_venue_preset(self):
        errs, _ = W.validate(self.spec)
        self.assertEqual(errs, [])
        d = self.spec["dimensions"]
        self.assertEqual(d["corridor"]["length_m"], 6.0)
        self.assertEqual(d["corridor"]["wall_height_m"], 3.0)
        self.assertAlmostEqual(d["corridor"]["spacing_m"] - d["corridor"]["width_m"], 2.0)
        self.assertEqual(d["red_zone"]["side_m"], 3.0)
        self.assertEqual(d["obstacle"]["height_m"], 2.0)

    def test_zone_and_fence_match_the_survey(self):
        zone = W.zone_polygon(self.spec)
        for lat, lon in SURVEY_ZONE:
            p = global_to_local(lat, lon, *HOME)
            self.assertLess(min(math.dist(p, c) for c in zone), 1.3)
        fence = W.fence_polygon(self.spec)
        self.assertEqual(len(fence), 4)
        back = global_to_local(*SURVEY_BACK_RIGHT, *HOME)
        self.assertLess(min(math.dist(back, c) for c in fence), 0.1)
        self.assertGreater(W.distance_to_edge(W.spawn_point(self.spec), fence), 5.0)

    def test_red_pad_with_the_aircraft_on_it_and_the_marker_in_front(self):
        t = self.spec["takeoff"]
        self.assertEqual(W.spawn_point(self.spec), (0.0, 0.0))
        self.assertEqual(W.takeoff_pad_size(self.spec), (0.5, 0.5))
        self.assertEqual(t["pad_colour"], "#FF0000")
        qx, qy = W.start_qr_point(self.spec)
        h = math.radians(t["yaw_deg"])
        self.assertAlmostEqual(qx * math.cos(h) + qy * math.sin(h), 1.5)
        self.assertAlmostEqual(-qx * math.sin(h) + qy * math.cos(h), 0.0)

    def test_two_thin_boards_alternate_in_the_exit_lane(self):
        boards = self.spec["return_corridor"]["obstacles"]
        self.assertEqual(len(boards), 2)
        self.assertEqual([b["u"] for b in boards], [2.0, 4.0])
        self.assertEqual([math.copysign(1, b["v"]) for b in boards], [1.0, -1.0])
        for b in boards:
            self.assertEqual(b["d"], 1.5)
            self.assertEqual(b["w"], 0.045)
            self.assertEqual(b["h"], 2.0)
        narrow = V.build("venue_test", reach_m=1.0, first_side="right")
        self.assertEqual([b["d"] for b in narrow["return_corridor"]["obstacles"]], [1.0, 1.0])
        self.assertLess(narrow["return_corridor"]["obstacles"][0]["v"], 0.0)

    def test_every_case_builds(self):
        for pads in V.PAD_LAYOUTS:
            for red in V.RED_PLACES:
                for target in "abcde":
                    spec = V.build("case", target=target, pads=pads, red=red)
                    self.assertEqual(W.validate(spec)[0], [], (pads, red, target))
        for reach in (1.0, 1.25, 1.5):
            for gap in (1.5, 2.0):
                self.assertEqual(W.validate(V.build("case", reach_m=reach, gap_m=gap))[0], [])

    def test_the_lane_lidar_still_sees_the_boards(self):
        # 1.5 m navigation height keeps the scan plane under the 2 m boards.
        A.validate(self.spec["dimensions"])


class OrganiserInputTests(unittest.TestCase):

    def test_two_back_points_four_corners_and_their_outline(self):
        import organiser_inputs as O
        spec = V.build("venue_test")
        org = O.organiser_inputs(spec, *HOME)
        behind = org["geofence"].splitlines()
        corners = org["delivery_zone"].splitlines()
        outline = org["geofence_outline"].splitlines()
        self.assertEqual((len(behind), len(corners), len(outline)), (2, 4, 4))
        pts = [tuple(map(float, l.split(","))) for l in corners]
        local, why = boundary_to_local_polygon(pts, *HOME)
        self.assertEqual(why, "")
        self.assertAlmostEqual(abs(W.polygon_area(local)), 17.8 * 23.9, delta=0.5)

    def test_every_gcs_slot_is_given_in_priority_order(self):
        import organiser_inputs as O
        from gcs_aggregator.organiser_points import KEYS
        spec = V.build("venue_test")
        pts = O.organiser_inputs(spec, *HOME)["points"]
        self.assertEqual(list(pts), list(KEYS))
        loc = {k: global_to_local(*map(float, v.split(",")), *HOME) for k, v in pts.items()}
        back = global_to_local(*SURVEY_BACK_RIGHT, *HOME)
        self.assertLess(math.dist(loc["fence_back_right"], back), 0.1)
        self.assertLess(math.dist(loc["home"], (0.0, 0.0)), 0.01)
        h = math.radians(spec["takeoff"]["yaw_deg"])

        def fwd(p):
            return p[0] * math.cos(h) + p[1] * math.sin(h)
        self.assertAlmostEqual(fwd(loc["entry_home"]), 5.5, places=1)
        self.assertAlmostEqual(fwd(loc["entry_zone"]), 11.5, places=1)
        self.assertAlmostEqual(fwd(loc["exit_zone"]), 11.5, places=1)
        self.assertAlmostEqual(fwd(loc["exit_home"]), 5.5, places=1)

    def test_the_turned_zone_is_published_as_its_corners(self):
        import publish_delivery_zone as P
        corners = P.zone_from_env({"AEROTHON_DELIVERY_ZONE": "1,2;3,4;5,6;7,8"})
        self.assertEqual(corners, [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0), (7.0, 8.0)])
        self.assertEqual(P.zone_corners((10.0, 0.0, 4.0, 2.0)),
                         [(8.0, -1.0), (12.0, -1.0), (12.0, 1.0), (8.0, 1.0)])
        payload = json.loads(P.boundary_payload(0, 0, 0, 0, *HOME, corners=[
            (5.0, 0.0), (20.0, 4.0), (16.0, 19.0), (1.0, 15.0)]))
        pts = [(v["lat"], v["lon"]) for v in payload["vertices"]]
        self.assertIsNotNone(boundary_to_local_polygon(pts, *HOME)[0])
        with self.assertRaises(ValueError):
            P.zone_from_env({"AEROTHON_DELIVERY_ZONE": "1,2;3,4;5,6"})


if __name__ == "__main__":
    unittest.main()
