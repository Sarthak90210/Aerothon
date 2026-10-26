#!/usr/bin/env python3
"""Red ground in front of the return lane (field world, 26 Oct 2026).

r9 and r11 put the 10 ft red square 4.8 m out on the return lane's axis. The
detector's cells, their 1 m inflation and the 1.5 m clearance made the
keep-out x 15.5..24.5, y -9.5..0.5 (recorded on /percep/redzone/detail in
r11), reaching to 1.8 m of the corridor face: every return stand-off (3-5 m
out, 2 m either side) and every square-up range (3.3 m and more) was on it.
ReturnToCorridorMouth refused, the mission failed, and the FC's RTL flew at
15 m over the red zone and the corridor.

Now the lane is entered from the clear strip at its face, on the lidar: the
camera alignment is skipped and says so, DuckUnderBoard widens its sector to
see both wall ends from that close, and nothing changes where a stand-off is
clear.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_return_gate_red_blocked.py -v
"""

import math
import os
import sys
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "aerothon_mission", "mission_bt"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import py_trees
import pytest

from mission_bt.mission_tree import (DuckUnderBoard, ReturnGateBlocked,
                                     ReturnToCorridorMouth, build_root)
from mission_bt.scan_geometry import gate_opening
from mission_bt.search_planner import routing_obstacles
from test_fail_closed_stages import FakeMav
from test_leg_routing import RoutedMav

S = py_trees.common.Status
# r11, in the mission's local frame: the outbound gate, the corridor's length
# and lane spacing from the GCS, the exit recorded 2.3 m past the face, and
# the confirmed red cells' extent with the detector's 1 m inflation.
OUTBOUND_BANNER = (7.0, 0.5)
LENGTH, LANE_W, OFFSET = 6.7056, 3.5052, -5.0
RECORDED_EXIT = (16.0, 0.9, 10.0, 0.0)
R11_RED = [(17.0, 23.0, -8.0, -1.0)]
FACE_X, LANE_Y = 7.0 + 6.7056, 0.5 - 5.0


def mouth_stage(red, at=(24.0, -4.0, 10.0)):
    mav = RoutedMav(exclusions=red, at=at)
    mav.corridor_exit_pose = RECORDED_EXIT
    mav.gate_heading = 0.0
    mav.outbound_banner_xy = OUTBOUND_BANNER
    stage = ReturnToCorridorMouth(mav, alt=10.0, standoff_m=5.0, clearance_m=1.5,
                                  lane_offset_m=OFFSET, corridor_length_m=LENGTH,
                                  lane_width_m=LANE_W)
    stage.initialise()
    return stage, mav


def test_the_recorded_keep_out_is_the_one_r11_refused_in():
    assert routing_obstacles(R11_RED, 1.5) == [(15.5, 24.5, -9.5, 0.5)]


def test_red_on_every_stand_off_enters_from_the_face_strip():
    stage, mav = mouth_stage(R11_RED)
    stage.update()
    x, y, yaw = mav.return_entry
    assert isinstance(mav.return_gate_blocked, str) and "every return stand-off" in mav.return_gate_blocked
    # 1.5 m out: the largest distance kept 0.25 m off the 15.5 m keep-out edge.
    assert x == pytest.approx(FACE_X + 1.5) and y == pytest.approx(LANE_Y)
    assert yaw == pytest.approx(math.pi)
    assert math.degrees(mav.return_entry_sector_rad) == pytest.approx(
        math.degrees(math.atan2(0.5 * LANE_W + 0.5, 1.5)) + 3.0)
    for x0, x1, y0, y1 in routing_obstacles(R11_RED, 1.5):
        assert not (x0 - 0.25 <= x <= x1 + 0.25 and y0 - 0.25 <= y <= y1 + 0.25)


def test_the_entry_is_routed_round_the_red_zone_not_through_it():
    stage, mav = mouth_stage(R11_RED)
    assert stage.update() is S.RUNNING
    assert mav.gotos, "commanded nothing"
    g = mav.gotos[0]
    assert (round(g[0], 1), round(g[1], 1)) != (round(FACE_X + 1.5, 1), round(LANE_Y, 1)), \
        "flew the straight line to the entry across the keep-out"


def test_it_faces_down_the_lane_before_handing_over():
    stage, mav = mouth_stage(R11_RED, at=(FACE_X + 1.5, LANE_Y, 10.0))
    mav._yaw = math.pi - 0.5
    assert stage.update() is S.RUNNING
    mav._yaw = math.pi - 0.02
    assert stage.update() is S.SUCCESS


def test_a_clear_stand_off_keeps_the_camera_alignment():
    # r10: the square beside pad C, nowhere near the return approach.
    stage, mav = mouth_stage([(24.5, 28.5, 0.0, 4.0)], at=(30.0, -4.0, 10.0))
    stage.update()
    assert mav.return_gate_blocked is None and mav.return_entry is None
    assert ReturnGateBlocked(mav).update() is S.FAILURE


def test_red_up_to_the_face_still_refuses():
    stage, mav = mouth_stage([(13.0, 23.0, -8.0, -1.0)])
    assert stage.update() is S.FAILURE
    assert "lies inside" in mav.abort_reason
    assert mav.return_gate_blocked is None


def test_no_known_face_still_refuses():
    stage, mav = mouth_stage(R11_RED)
    mav.outbound_banner_xy = None
    assert stage.update() is S.FAILURE


def test_the_blocked_gate_skips_the_camera_and_says_so():
    mav = FakeMav()
    mav.return_gate_blocked = "red ground covers every return stand-off"
    mav.return_entry = (15.2, -4.5, math.pi)
    assert ReturnGateBlocked(mav).update() is S.SUCCESS
    assert any("NOT identified or aligned" in str(line) for line in mav.logs)
    mav.return_gate_blocked = None
    assert ReturnGateBlocked(mav).update() is S.FAILURE


def test_only_the_return_crossing_widens_its_sector_and_only_when_blocked():
    mav = MagicMock()
    mav.board_face_t = None
    mav.return_gate_blocked = "red ground covers every return stand-off"
    mav.return_entry_sector_rad = math.radians(59.0)
    back = DuckUnderBoard(mav, return_lap=True)
    out = DuckUnderBoard(mav)
    back.initialise(), out.initialise()
    assert back._half_width == pytest.approx(math.radians(59.0))
    assert out._half_width == pytest.approx(math.radians(35.0))
    mav.return_gate_blocked = None
    back.initialise()
    assert back._half_width == pytest.approx(math.radians(35.0))


def lane_scan(standoff_m, half_lane=0.5 * LANE_W, length=LENGTH, next_wall=3.25):
    """A 720-beam scan from `standoff_m` in front of a lane's face, facing
    down it: its two walls and the next lane's near wall, no board."""
    walls = [(standoff_m, standoff_m + length, half_lane),
             (standoff_m, standoff_m + length, -half_lane),
             (standoff_m, standoff_m + length, next_wall)]
    n, ranges = 720, []
    inc = 2 * math.pi / n
    for i in range(n):
        a = -math.pi + i * inc
        best = float("inf")
        if abs(math.sin(a)) > 1e-6:
            for x0, x1, wy in walls:
                r = wy / math.sin(a)
                if r > 0 and x0 <= r * math.cos(a) <= x1:
                    best = min(best, r)
        ranges.append(best if best < 12.0 else float("inf"))
    return -math.pi, inc, ranges


def test_from_the_face_only_the_widened_sector_reads_the_gate_at_the_wall_ends():
    a0, inc, ranges = lane_scan(1.5)
    narrow = gate_opening(a0, inc, ranges, 0.0, math.radians(35.0), need_clear_m=0.0)
    wide = gate_opening(a0, inc, ranges, 0.0,
                        math.atan2(0.5 * LANE_W + 0.5, 1.5) + math.radians(3.0),
                        need_clear_m=0.0)
    assert wide["open"] and wide["gate_m"] == pytest.approx(1.5, abs=0.1)
    assert narrow["gate_m"] is None or narrow["gate_m"] > 2.2, \
        "a 35 deg sector saw the wall ends from 1.5 m"
    assert abs(wide["centre_m"]) < 0.1


def test_the_tree_skips_only_the_camera_search_and_alignment():
    params = {'takeoff_alt': 5.0, 'search_alt': 10.0, 'drop_alt': 5.0,
              'image_width_px': 1280, 'image_height_px': 720, 'camera_hfov': 1.0472,
              'target_marker_m': 2.2, 'px_per_module_floor': 5.3, 'lane_overlap': 0.30,
              'zone_boundary_clearance': 1.0, 'corridor_alt': 1.5, 'scan_floor_alt': 2.0,
              'land_commit_alt': 1.5, 'banner_sweep_limit': math.pi,
              'gate_advance_m': LENGTH, 'banner_w_m': LANE_W}
    root = build_root(FakeMav(), MagicMock(), params)
    nodes = {n.name: n for n in root.iterate()}
    gate = nodes["ReturnGate"]
    assert [c.name for c in gate.children] == ["ReturnGateBlocked", "ReturnGateAlign"]
    inside = [n.name for n in nodes["ReturnGateAlign"].iterate()]
    assert "DescendToReturnIdent" in inside and "FindReturnBanner" in inside
    assert any(name.startswith("Return") and "Banner" in name for name in inside if name != "FindReturnBanner") \
        or "AlignToBanner" in inside
    mission = [c for c in root.children if c.name == "Mission"][0]
    order = [n.name for n in mission.iterate()]
    for before, after in (("ReturnToCorridorMouth", "ReturnGate"),
                          ("ReturnGate", "DescendToReturnCorridor"),
                          ("DescendToReturnCorridor", "DuckUnderBoard"),
                          ("DuckUnderBoard", "ReturnCorridor")):
        assert order.index(before) < len(order) - 1 - order[::-1].index(after), (before, after)
    mouth = nodes["ReturnToCorridorMouth"]
    assert mouth.corridor_length_m == pytest.approx(LENGTH) and mouth.lane_width_m == pytest.approx(LANE_W)
    assert [n for n in mission.iterate() if isinstance(n, DuckUnderBoard) and n.return_lap]
