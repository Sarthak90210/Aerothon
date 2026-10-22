#!/usr/bin/env python3
"""Gate-pair selection under a rod-hung board.

WHAT WAS WATCHED

    World "shipped", outbound gate, three runs (shipped_chase, shipped_20kmh_r2,
    shipped_20kmh_r3). Squared up on the green board, ducked under it, then:
    "0.98 m right of the gap's middle; moving across to it (1/4)", "0.48 m
    right ... (2/4)", "one face became 8 posts with a 4.1 m gap", and at 1.2 m
    "gate at 4.89 m, something standing at 4.92 m" -- mission FAILED, the
    aircraft parked in line with the outbound corridor's right wall.

THE DEFECT

    Below the board there are no posts, only wall ends, and the linked return
    lane's north wall ends at exactly the depth of this mouth's right wall.
    Picking the pair with the nearest MEAN depth cannot tell this gate's 2 m
    mouth from the 4 m "gap" that spans its right wall end; a degree of
    residual square-up yaw decided it. A pair with another surface standing
    between its fronts, at their depth, is two openings, not one.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_gate_pair_selection.py -v
"""

import base64
import json
import math
import os
import struct
import sys
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src", "aerothon_mission", "mission_bt"))
sys.path.insert(0, HERE)

from mission_bt import scan_geometry                          # noqa: E402
from mission_bt.scan_geometry import despeckle                # noqa: E402
from test_scan_geometry import ANGLE_INC, ANGLE_MIN, post, scan_of, wall  # noqa: E402

# Recorded /scan from logs/return_lap_20261020 (shipped_20kmh_r2, shipped_2mps,
# shipped_fast); provenance inside the file.
FIXTURE = os.path.join(HERE, "fixtures", "gate_pair_wall_ends_shipped_20261021.json")
HALF = math.radians(35.0)


def gate_opening(*a, **k):
    return scan_geometry.gate_opening(*a, **k)


def recorded(name):
    record = json.load(open(FIXTURE, encoding="utf-8"))
    s = record["sets"][name]
    for blob, stamp, pose in zip(s["ranges"], s["stamps"], s["pose_local_xyz_yawdeg"]):
        raw = zlib.decompress(base64.b64decode(blob))
        mm = struct.unpack(f"<{len(raw) // 2}H", raw)
        ranges = [float("inf") if v == 0 else v / 1000.0 for v in mm]   # 0 = no return
        yield stamp, pose, s, (despeckle(ranges), ranges)                 # as Mav._on_scan


def look(s, scan, corridor_m=0.9):
    # DuckUnderBoard.update -> Mav.opening_ahead, venue crossing_strip_m 0.9:
    # the despeckled scan plus the raw one for lone returns at gate depth.
    ranges, raw = scan
    return gate_opening(s["angle_min"], s["angle_increment"], ranges, 0.0, HALF,
                        need_clear_m=0.0, range_min=s["range_min"],
                        range_max=s["range_max"], corridor_m=corridor_m,
                        raw_ranges=raw)


def crosses_here(o):
    """DuckUnderBoard's own arithmetic: no recentre, gate + 0.6 + 0.4 clear."""
    c = o.get("centre_m")
    return (o["open"] and o.get("gate_m") is not None and c is not None
            and abs(c) <= 0.25 and o["clear_m"] >= o["gate_m"] + 1.0)


class RecordedGatePairTests(unittest.TestCase):

    def _mouth(self, name, corridor_m=0.9):
        for stamp, pose, s, scan in recorded(name):
            with self.subTest(set=name, stamp=stamp, strip=corridor_m):
                o = look(s, scan, corridor_m)
                self.assertTrue(o["open"], o["reason"])
                self.assertTrue(1.9 <= o["gap_m"] <= 2.3,
                                f"{o['gap_m']:.2f} m is not this 2 m mouth (pose {pose})")
                self.assertLessEqual(abs(o["centre_m"]), 0.25,
                                     "would recentre off the line it squared up on")
                self.assertTrue(crosses_here(o), o)

    def test_r2_first_look_under_the_board_keeps_the_mouth_it_squared_up_on(self):
        """Failing before: gap 4.01-4.07 m, centre -0.89..-0.98 m on all 20."""
        self._mouth("r2_first_under_edge_look")
        self._mouth("r2_first_under_edge_look", corridor_m=1.5)

    def test_2mps_first_look_no_longer_detours_a_metre_right(self):
        """Failing before on all 14: gap ~4.0 m, centre about -0.92 m."""
        self._mouth("mps2_first_under_edge_look")

    def test_the_run_that_crossed_still_crosses_the_same_way(self):
        self._mouth("fast_under_edge_looks")

    def test_the_board_is_still_the_board(self):
        for stamp, pose, s, scan in recorded("r2_board_looks"):
            with self.subTest(stamp=stamp):
                o = look(s, scan)
                self.assertFalse(o["open"])
                self.assertEqual(o["clusters"], 1)
                self.assertIn("board", o["reason"])


def _rect(x0, x1, y0, y1):
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
            ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def _lanes(ya, psi, d=4.9, length=5.2):
    """Two 2 m lanes side by side, 0.1 m walls, every wall end at depth d --
    a NEIGHBOURING lane's wall end level with this gate's. Expressed relative
    to the mouth's own centre; the code under test sees only ranges."""
    segs = []
    for y0, y1 in ((1.0, 1.1), (-1.1, -1.0), (-3.0, -2.9), (-5.1, -5.0)):
        segs += _rect(d, d + length, y0, y1)
    c, s = math.cos(psi), math.sin(psi)
    return [tuple((px * c + (py - ya) * s, -px * s + (py - ya) * c) for px, py in seg)
            for seg in segs]


class NeighbouringLaneWallEndTests(unittest.TestCase):

    def test_a_neighbouring_lanes_wall_end_is_not_this_gates_post(self):
        """Failing before on 19 of these 35 poses (the 4 m pair wins).
        Passing after on all 35."""
        for ya in (-0.3, -0.2, 0.0, 0.2, 0.3):
            for deg in (-3, -2, -1, 0, 1, 2, 3):
                psi = math.radians(deg)
                with self.subTest(ya=ya, psi_deg=deg):
                    o = gate_opening(ANGLE_MIN, ANGLE_INC,
                                     despeckle(scan_of(_lanes(ya, psi))), 0.0, HALF,
                                     need_clear_m=0.0, corridor_m=0.9)
                    want = -4.9 * math.sin(psi) - ya * math.cos(psi)
                    self.assertTrue(1.8 <= o["gap_m"] <= 2.4, o)
                    self.assertAlmostEqual(o["centre_m"], want, delta=0.15)

    def test_a_surface_between_two_others_at_their_depth_splits_the_opening(self):
        segs = [post(5.0, 0.0, -1.9), post(5.3, 0.0, 0.6), post(5.0, 0.0, 1.9)]
        o = gate_opening(ANGLE_MIN, ANGLE_INC, scan_of(segs), 0.0, HALF, need_clear_m=0.0)
        self.assertAlmostEqual(o["centre_m"], -0.65, delta=0.15)
        self.assertLess(o["gap_m"], 3.0)


class BlockedGateStillRefusesTests(unittest.TestCase):

    def _o(self, segs, need=10.0):
        raw = scan_of(segs)
        return gate_opening(ANGLE_MIN, ANGLE_INC, despeckle(raw), 0.0, HALF,
                            need_clear_m=need, corridor_m=0.9, raw_ranges=raw)

    def test_a_wall_end_dead_ahead_on_one_beam_still_blocks(self):
        """r2 after its starboard recentres: the outbound right wall's 0.1 m end
        stood dead ahead on one beam, despeckle replaced it with the wall face
        ~2 m behind, and the strip read clear into it (clear 6.15-7.08 m
        against ~5.95 needed). It must refuse on all ten scans."""
        for stamp, pose, s, scan in recorded("r2_wall_end_dead_ahead"):
            for strip in (0.9, 1.5):
                with self.subTest(stamp=stamp, strip=strip):
                    o = look(s, scan, strip)
                    self.assertIsNotNone(o.get("gate_m"), o)
                    self.assertLess(o["clear_m"], o["gate_m"] + 1.0, o)
                    self.assertFalse(crosses_here(o), o)

    def test_a_thin_pole_in_the_mouth_still_blocks(self):
        segs = [post(5.0, 0.0, -1.9), post(5.0, 0.0, 0.05, width_m=0.06),
                post(5.0, 0.0, 1.9)]
        raw = scan_of(segs)
        o = gate_opening(ANGLE_MIN, ANGLE_INC, despeckle(raw), 0.0, HALF,
                         need_clear_m=0.0, corridor_m=0.9, raw_ranges=raw)
        self.assertFalse(crosses_here(o), o)

    def test_dust_in_front_of_the_gate_is_still_not_a_structure(self):
        """A lone return well short of the gate stays despeckled."""
        raw = scan_of([post(5.0, 0.0, -1.9), post(5.0, 0.0, 1.9)])
        mid = min(range(len(raw)), key=lambda i: abs(ANGLE_MIN + i * ANGLE_INC))
        raw[mid] = 1.3
        o = gate_opening(ANGLE_MIN, ANGLE_INC, despeckle(raw), 0.0, HALF,
                         need_clear_m=0.0, corridor_m=0.9, raw_ranges=raw)
        self.assertTrue(o["open"], o)
        self.assertGreaterEqual(o["clear_m"], o["gate_m"] + 1.0, o)

    def test_a_panel_across_the_line_below_the_board(self):
        o = self._o([post(5.0, 0.0, -1.9), wall(5.0, 0.0, half_length_m=0.6),
                     post(5.0, 0.0, 1.9)])
        self.assertFalse(o["open"])
        self.assertIn("board", o["reason"])

    def test_a_block_on_the_line_just_past_the_posts(self):
        o = self._o([post(5.0, 0.0, -1.9), post(5.9, 0.0, 0.0, width_m=0.4),
                     post(5.0, 0.0, 1.9)])
        self.assertFalse(o["open"])
        self.assertLess(o["clear_m"], o["gate_m"] + 1.0)

    def test_a_centre_post_leaving_halves_too_narrow_to_fly(self):
        o = self._o([post(5.0, 0.0, -0.8, width_m=0.15), post(5.0, 0.0, 0.0, width_m=0.15),
                     post(5.0, 0.0, 0.8, width_m=0.15)])
        self.assertFalse(o["open"])


if __name__ == "__main__":
    unittest.main()
