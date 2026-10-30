#!/usr/bin/env python3
"""The venue's delivery zone is turned to the ground, not to north.

On 30 Oct 2026 the operator surveyed the field: two fence points behind
take-off, the corridors, and the delivery zone's four corners. The corridors
run 286.5 deg true, so the zone is turned 16.5 deg off east-west and its
corners miss a rectangle by up to 1.2 m. The four-corner path refused it
("not an axis-aligned ENU rectangle"). These pin the polygon reading, the red
filter that ignores the red take-off pad, lanes trimmed inside the zone and
3 m inside the arena fence the zone reaches, and readiness.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_turned_zone.py -v
"""

import math
import os
import random
import sys
import unittest
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_mission", "mission_bt"))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_gcs", "gcs_aggregator"))

import py_trees                                                  # noqa: E402

from mission_bt.delivery_zone import (ROLE_ARENA,                 # noqa: E402
                                      boundary_to_local_polygon,
                                      boundary_to_local_zone, convex_hull,
                                      point_in_polygon,
                                      point_inside_with_margin, polygon_area,
                                      rectangle_touches_polygon)
from mission_bt.geofence import global_to_local, local_to_global  # noqa: E402

# The operator's survey, 30 Oct 2026 (the take-off pad is home).
HOME = (13.1705900, 77.5331760)
ZONE = [(13.1705131, 77.5330233), (13.1707149, 77.5330967),
        (13.1707636, 77.5329365), (13.1705581, 77.5328695)]
BACK_RIGHT = (13.1707773, 77.5332852)
# The back-left point as typed was 122 m off; the arena's mirror of the
# back-right point about the take-off axis (corridors at 286.5 deg true).
_U = (math.cos(math.radians(163.48)), math.sin(math.radians(163.48)))
_L = (-_U[1], _U[0])
BACK_LEFT = local_to_global(-5.42 * _U[0] + 23.36 * _L[0],
                            -5.42 * _U[1] + 23.36 * _L[1], *HOME)


def local(points):
    return [global_to_local(lat, lon, *HOME) for lat, lon in points]


def venue_fence():
    return convex_hull(local([BACK_LEFT, BACK_RIGHT] + ZONE))


class PolygonReadingTests(unittest.TestCase):

    def test_the_venue_zone_is_no_rectangle_but_a_convex_quad(self):
        self.assertIsNone(boundary_to_local_zone(ZONE, *HOME)[0])
        pts, why = boundary_to_local_polygon(ZONE, *HOME)
        self.assertEqual(why, "")
        self.assertEqual(len(pts), 4)
        self.assertGreater(polygon_area(pts), 0.0)          # counter-clockwise
        self.assertAlmostEqual(polygon_area(pts), 18.0 * 24.0, delta=25.0)

    def test_corner_order_does_not_matter(self):
        want, _ = boundary_to_local_polygon(ZONE, *HOME)
        shuffled = list(ZONE)
        random.Random(3).shuffle(shuffled)
        got, why = boundary_to_local_polygon(shuffled, *HOME)
        self.assertEqual(why, "")
        self.assertEqual(sorted(got), sorted(want))
        self.assertGreater(polygon_area(got), 0.0)

    def test_a_dart_a_sliver_and_a_huge_field_are_refused(self):
        def geo(points):
            return [local_to_global(x, y, *HOME) for x, y in points]
        dart = geo([(0, 0), (20, 0), (10, 4), (10, 20)])
        sliver = geo([(0, 0), (20, 0), (20, 2), (0, 2)])
        huge = geo([(0, 0), (200, 0), (200, 30), (0, 30)])
        self.assertIn("convex", boundary_to_local_polygon(dart, *HOME)[1])
        self.assertIn("too short", boundary_to_local_polygon(sliver, *HOME)[1])
        self.assertIn("too long", boundary_to_local_polygon(huge, *HOME)[1])

    def test_take_off_and_corridors_lie_inside_the_fence_not_the_zone(self):
        zone, _ = boundary_to_local_polygon(ZONE, *HOME)
        fence = venue_fence()
        self.assertTrue(point_inside_with_margin(0.0, 0.0, fence, 2.0))
        self.assertFalse(point_in_polygon(0.0, 0.0, zone))
        for corner in zone:
            self.assertTrue(point_in_polygon(*corner, fence)
                            or min(math.dist(corner, v) for v in fence) < 1e-6)


class RedFilterTests(unittest.TestCase):

    def test_red_take_off_pad_is_not_a_restricted_zone(self):
        from mission_bt.mav_commander import inside_delivery_zone
        zone, _ = boundary_to_local_polygon(ZONE, *HOME)
        pad = (-0.75, 0.75, -0.75, 0.75)          # 0.5 m pad, 1 m inflation
        cx = sum(p[0] for p in zone) / 4
        cy = sum(p[1] for p in zone) / 4
        square = (cx - 2.0, cx + 2.0, cy - 2.0, cy + 2.0)
        self.assertEqual(inside_delivery_zone([pad, square], None, zone), [square])
        # A rectangle zone still wins, and no zone keeps everything.
        self.assertEqual(inside_delivery_zone([pad], (5, 30, -10, 10), zone), [])
        self.assertEqual(inside_delivery_zone([pad], None), [pad])

    def test_rectangle_polygon_overlap(self):
        diamond = [(0.0, -5.0), (5.0, 0.0), (0.0, 5.0), (-5.0, 0.0)]
        self.assertTrue(rectangle_touches_polygon((-1, 1, -1, 1), diamond))     # inside
        self.assertTrue(rectangle_touches_polygon((-9, 9, -9, 9), diamond))     # holds it
        self.assertTrue(rectangle_touches_polygon((3, 6, -0.5, 0.5), diamond))  # edge
        self.assertTrue(rectangle_touches_polygon((-6, 6, -0.2, 0.2), diamond))  # bar across
        self.assertFalse(rectangle_touches_polygon((4, 6, 4, 6), diamond))      # corner gap
        self.assertFalse(rectangle_touches_polygon((10, 12, 0, 1), diamond))


def commander():
    from mission_bt.mav_commander import Mav
    mav = Mav.__new__(Mav)
    mav.geofence_local = None
    mav.geofence_global = None
    mav.judges_role = None
    mav.judges_zone_local = None
    mav.delivery_zone_global = None
    mav.delivery_zone_local = None
    mav.zone_corners_local = None
    mav.delivery_zone_reason = "delivery-zone boundary is missing"
    mav.corridor_exit_pose = None
    mav.gate_heading = None
    mav._logged = set()
    mav.node = NS(get_logger=lambda: NS(info=lambda *a: None))
    mav.home = NS(geo=NS(latitude=HOME[0], longitude=HOME[1]),
                  position=NS(x=0.0, y=0.0))
    return mav


def payload(points):
    import json
    return NS(data=json.dumps({"vertices": [{"lat": a, "lon": b} for a, b in points]}))


class CommanderTests(unittest.TestCase):

    def setUp(self):
        self.mav = commander()
        fence = [local_to_global(x, y, *HOME) for x, y in venue_fence()]
        self.mav._on_geofence(NS(data=__import__("json").dumps(
            {"vertices": [{"lat": a, "lon": b} for a, b in fence]})))
        self.mav._on_delivery_zone(payload(ZONE))

    def test_turned_corners_are_searched_as_their_polygon(self):
        mav = self.mav
        self.assertIsNone(mav.delivery_zone_local)
        self.assertEqual(len(mav.zone_corners_local), 4)
        self.assertFalse(mav.fence_only)
        self.assertFalse(mav.arena_search)
        self.assertEqual(mav.search_polygon(), mav.zone_corners_local)
        self.assertEqual(mav.search_margin_m, 1.0)
        zone = mav.delivery_search_zone(1.0)
        xs = [p[0] for p in mav.zone_corners_local]
        self.assertAlmostEqual(zone[0], min(xs) + 1.0, places=6)

    def test_the_arena_fence_is_kept_and_lanes_keep_3_m_inside_it(self):
        mav = self.mav
        self.assertEqual(mav.judges_role, ROLE_ARENA)
        fence, margin = mav.search_fence()
        self.assertEqual(margin, 3.0)
        self.assertEqual(len(fence), 4)

    def test_the_mission_may_arm(self):
        from mission_bt.mission_tree import RequireDeliveryZone
        leaf = RequireDeliveryZone(self.mav, 1.0)
        leaf.tick_once()
        self.assertEqual(leaf.status, py_trees.common.Status.SUCCESS)

    def test_a_square_zone_keeps_the_rectangle_path(self):
        mav = commander()
        square = [local_to_global(x, y, *HOME)
                  for x, y in ((10, -10), (30, -10), (30, 10), (10, 10))]
        mav._on_delivery_zone(payload(square))
        self.assertIsNone(mav.zone_corners_local)
        self.assertEqual(tuple(round(v, 3) for v in mav.delivery_zone_local),
                         (10.0, 30.0, -10.0, 10.0))
        self.assertIsNone(mav.search_polygon())
        self.assertIsNone(mav.search_fence())


class LaneTests(unittest.TestCase):

    def test_every_lane_stays_in_the_zone_and_clear_of_the_fence(self):
        from mission_bt.delivery_zone import bounding_zone
        from mission_bt.mission_tree import LawnmowerSearch
        from test_fail_closed_stages import FakeMav
        zone, _ = boundary_to_local_polygon(ZONE, *HOME)
        fence = venue_fence()
        fake = FakeMav()
        fake.exclusions = []
        fake._pos = (-10.0, 2.0, 8.0)
        fake.search_polygon = lambda: zone
        fake.search_fence = lambda: (fence, 3.0)
        fake.search_margin_m = 1.0
        x0, x1, y0, y1 = bounding_zone(zone)
        leaf = LawnmowerSearch(fake, (x0 + 1, x1 - 1, y0 + 1, y1 - 1), 8.0,
                               exclusions=lambda: [], search_budget_m=0.0)
        leaf.initialise()
        self.assertGreaterEqual(len(leaf.wps) // 2, 3)
        for a, b in zip(leaf.wps[0::2], leaf.wps[1::2]):
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
                self.assertTrue(point_inside_with_margin(x, y, zone, 0.9),
                                f"lane point ({x:.1f}, {y:.1f}) leaves the zone")
                self.assertTrue(point_inside_with_margin(x, y, fence, 2.9),
                                f"lane point ({x:.1f}, {y:.1f}) is within 3 m of the fence")


class ReadinessTests(unittest.TestCase):

    def test_turned_corners_pass_readiness(self):
        from gcs_aggregator.readiness_node import Readiness
        fake = NS(obs={}, delivery_vertices=ZONE,
                  delivery_parse_reason="", home=NS(geo=NS(latitude=HOME[0], longitude=HOME[1])))
        Readiness._resolve_delivery_zone(fake)
        self.assertTrue(fake.obs["delivery_zone_valid"])
        self.assertIn("turned", fake.obs["delivery_zone_value"])

    def test_a_dart_still_fails_readiness(self):
        from gcs_aggregator.readiness_node import Readiness
        dart = [local_to_global(x, y, *HOME) for x, y in ((0, 0), (20, 0), (10, 4), (10, 20))]
        fake = NS(obs={}, delivery_vertices=dart, delivery_parse_reason="",
                  home=NS(geo=NS(latitude=HOME[0], longitude=HOME[1])))
        Readiness._resolve_delivery_zone(fake)
        self.assertFalse(fake.obs["delivery_zone_valid"])
        self.assertIn("convex", fake.obs["delivery_zone_reason"])


if __name__ == "__main__":
    unittest.main()
