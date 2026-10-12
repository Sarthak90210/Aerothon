"""Phase 2: the arena the organisers clarified, entered at the GCS.

A banner whose height is not given (perhaps a foot tall, hung from the rod at
the 10 ft wall top), an orange banner beside every green one, and a detector
that takes the banner's size from the operator instead of a launch file.

    python3 -m pytest sim/test_phase2_arena.py -v
"""
import json
import os
import sys
import types
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

from perception_banner import banner_shape, colours           # noqa: E402
from perception_banner.banner_node import BannerNode          # noqa: E402

SUPPLIED = {"green": "#07A03D", "orange": "#EB5A0A", "red": "#C4161C"}


# ---- a banner thinner than the board the limits were measured on -------- #

@pytest.mark.parametrize("height_m", [0.3048, 0.457, 1.15])
def test_a_face_on_banner_of_any_height_passes_the_upright_limit(height_m):
    w = 3.5
    assert w / height_m < banner_shape.max_aspect(w, height_m)


def test_the_limits_never_tighten_below_what_was_measured():
    assert banner_shape.max_aspect(3.7, 1.15) == pytest.approx(8.0)
    assert banner_shape.max_aspect(2.0, 1.0) == pytest.approx(8.0)
    assert banner_shape.max_aspect(3.7, 1.15, ground=True) == pytest.approx(16.0)


def test_a_foot_tall_laid_sheet_seen_from_the_ground_pose_is_accepted():
    import math
    # Face-on from the 35 deg GROUND pose a laid sheet foreshortens by the
    # sine of the look-down angle: 3.5 x 0.3 m reads about 20:1.
    seen = 3.5 / (0.3048 * math.sin(math.radians(35.0)))
    assert seen > banner_shape.GROUND_MAX
    assert seen < banner_shape.max_aspect(3.5, 0.3048, ground=True)


def test_bad_sizes_fall_back_to_the_measured_limits():
    assert banner_shape.stretch(None, 1.0) == 1.0
    assert banner_shape.stretch(3.5, 0.0) == 1.0


# ---- the detector takes the banner's size from the GCS ------------------ #

def _node():
    node = types.SimpleNamespace(set_parameters=MagicMock(),
                                 get_logger=lambda: MagicMock())
    return node


def _applied(applied=True, w=3.5, h=0.3048):
    return types.SimpleNamespace(data=json.dumps(
        {"applied": applied, "dimensions": {"banner": {"width_m": w, "height_m": h}}}))


def test_the_banner_size_follows_the_dimensions_the_mission_applied():
    node = _node()
    BannerNode._on_arena_dimensions(node, _applied())
    (params,), _ = node.set_parameters.call_args
    got = {p.name: p.value for p in params}
    assert got == {"banner_width_m": 3.5, "banner_height_m": 0.3048}


def test_dimensions_the_mission_refused_do_not_resize_the_detector():
    node = _node()
    BannerNode._on_arena_dimensions(node, _applied(applied=False))
    BannerNode._on_arena_dimensions(node, types.SimpleNamespace(data="not json"))
    BannerNode._on_arena_dimensions(node, _applied(h=0.0))
    node.set_parameters.assert_not_called()


# ---- green is the banner to fly to; orange never a candidate ------------ #

def _patch(hex_code):
    bgr = np.full((8, 8, 3), colours.parse_hex(hex_code)[::-1], np.uint8)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)


def test_with_colours_supplied_the_search_mask_takes_green_and_not_orange():
    node = types.SimpleNamespace(_colours=dict(SUPPLIED))
    bands = BannerNode.colour_ranges(node)
    assert colours.mask(_patch(SUPPLIED["green"]), bands).all()
    assert not colours.mask(_patch(SUPPLIED["orange"]), bands).any()


def test_orange_is_still_named_when_asked_about_a_panel():
    node = types.SimpleNamespace(_colours=dict(SUPPLIED))
    node.colour_ranges = lambda name=None: BannerNode.colour_ranges(node, name)
    panel = np.full((20, 40, 3), colours.parse_hex(SUPPLIED["orange"])[::-1], np.uint8)
    name, frac = BannerNode.dominant_colour(node, panel)
    assert name == "orange" and frac > 0.9


# ---- the world is built from the same dimensions the GCS applies -------- #

import world_spec as W                                        # noqa: E402
import world_from_dimensions as WFD                           # noqa: E402
from mission_bt import arena_dimensions as A                  # noqa: E402


def _clarified(height_m=0.3048, placement="both"):
    d = A.validate(A.BUILTIN_PRESETS["SAE Aerothon 2026 (clarified)"])
    wall = d["corridor"]["wall_height_m"]
    d["banner"].update(height_m=height_m, suspended_bottom_m=wall - height_m,
                       placement=placement)
    return d


def _layout():
    with open(os.path.join(HERE, "worlds", "banner_both.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("height_m", [0.3048, 1.15])
def test_the_world_matches_the_dimensions_entered(height_m):
    d = _clarified(height_m)
    spec = W.normalise(WFD.build(d, _layout(), "t"))
    assert W.validate(spec)[0] == []
    c, r, b = spec["corridor"], spec["return_corridor"], spec["banner"]
    assert r["linked"] is True and r["width"] == c["width"] == 3.5
    assert c["wall_height"] == pytest.approx(3.048)
    # Hung from the rod at the wall top, as wide as the corridor.
    assert b["mount"] == "rod" and b["orange"] is True
    assert b["board_bottom_m"] + b["height_m"] == pytest.approx(c["wall_height"])
    assert b["width_m"] == c["width"]
    assert spec["qr"] == {"start_m": 1.0, "target_m": 1.0}
    assert len(spec["red_zones"]) == 1
    assert spec["red_zones"][0]["w"] == pytest.approx(1.524)
    # Obstacles in the exit corridor reach half its width from a wall.
    for o in r["obstacles"]:
        assert o["d"] == pytest.approx(c["width"] / 2)
        assert abs(o["v"]) + o["d"] / 2 == pytest.approx(c["width"] / 2)


def test_the_delivery_zone_is_kept_clear_of_the_corridor_ends():
    spec = W.normalise(WFD.build(_clarified(), _layout(), "t"))
    z = spec["delivery_zone"]
    import math
    ends = [W._place((float(l["length"]), 0.0), l["x"], l["y"], math.radians(l["yaw_deg"]))
            for l in (spec["corridor"], spec["return_corridor"])]
    assert z["x"] - z["w"] / 2 >= max(x for x, _ in ends) + WFD.ZONE_CLEAR_M - 1e-6


def test_a_rod_hung_banner_above_the_walls_is_refused():
    spec = W.normalise(WFD.build(_clarified(), _layout(), "t"))
    spec["banner"]["board_bottom_m"] = 2.9
    errs, _ = W.validate(spec)
    assert any("above" in e for e in errs)


def test_the_headless_arena_builds_the_rod_hung_banners_and_the_orange_ones():
    from headless_world import Arena
    spec = W.normalise(WFD.build(_clarified(0.3048, "both"), _layout(), "t"))
    a = Arena(spec, "b")
    assert not [box for box in a.boxes if box[3] == "post"], "the walls carry it"
    boards = [box for box in a.boxes if box[3] == "board"]
    assert len(boards) == 4, "green at each entrance, orange at each far end"
    for _, z0, z1, _ in boards:
        assert z1 == pytest.approx(3.048) and z1 - z0 == pytest.approx(0.3048)
    assert a.board_w == 3.5 and a.board_h == pytest.approx(0.3048)


# ---- the hung-banner square-up finds a thin banner ---------------------- #

def _align(banner_h_m, banner_bottom_m=None, z=5.0):
    from mission_bt.mission_tree import AlignToBanner
    mav = MagicMock()
    leaf = AlignToBanner(mav, clock=lambda: 0.0, banner_w_m=3.5, banner_h_m=banner_h_m,
                         banner_bottom_m=banner_bottom_m, alt_floor_m=2.4384)
    leaf._anchor = (0.0, 0.0, z)
    leaf._surface = None
    leaf._descents = 0
    leaf._lower_camera = lambda: None
    return leaf


def test_the_descent_never_steps_over_a_thin_banner():
    leaf = _align(0.3048)
    leaf._no_surface({"ok": False, "points": 0, "reason": "nothing"})
    _, _, z = leaf._anchor
    assert 5.0 - z <= 0.8 * 0.3048 + 1e-9


def test_with_the_banner_height_from_the_gcs_it_goes_straight_to_it():
    leaf = _align(0.3048, banner_bottom_m=3.048 - 0.3048)
    leaf._no_surface({"ok": False, "points": 0, "reason": "nothing"})
    _, _, z = leaf._anchor
    lidar = z + leaf.lidar_above_body_m
    assert 3.048 - 0.3048 < lidar < 3.048, "the scan plane cuts the banner"


# ---- the precision landing on a 1 m start QR ---------------------------- #

def test_the_landing_commits_where_a_turned_start_qr_still_fits_the_frame():
    import math
    from mission_bt.mission_tree import PrecisionDescent
    from mission_bt.search_planner import vfov
    leaf = PrecisionDescent(MagicMock(), commit_alt=1.5, marker_m=1.0,
                            hfov_rad=0.851919, image_w_px=1280, image_h_px=720)
    # The smoke run's 25 deg turn: the marker spans 1.0 x (cos + sin) of frame.
    short_side = 2 * leaf.commit_alt * math.tan(vfov(0.851919, 1280, 720) / 2)
    turned = 1.0 * (math.cos(math.radians(25)) + math.sin(math.radians(25)))
    assert turned < short_side
    assert 1.0 * math.sqrt(2) <= short_side + 1e-9, "fits at any rotation"


def test_the_landing_uses_the_start_qr_size_from_the_gcs():
    d = A.validate(A.BUILTIN_PRESETS["SAE Aerothon 2026 (clarified)"])
    assert A.mission_params(d, {})["start_marker_m"] == 1.0


# ---- an orbit leg refuses a wall alongside, not only ahead -------------- #

def _scan_mav(ranges_by_deg, yaw=0.0):
    import math
    n = 360
    ranges = [float("inf")] * n
    for deg, r in ranges_by_deg.items():
        ranges[int(deg) % n] = r
    scan = types.SimpleNamespace(ranges=ranges, range_min=0.05, range_max=12.0,
                                 angle_min=0.0, angle_increment=math.radians(1.0))
    mav = MagicMock()
    mav._scan = scan
    mav.pos.return_value = (0.0, 0.0, 3.0)
    mav.yaw.return_value = yaw
    return mav


def test_a_leg_beside_a_wall_is_refused():
    from mission_bt.banner_orbit import leg_clear
    # Leg due +x; the wall runs alongside at 0.7 m on the left (90 deg).
    beside = _scan_mav({88: 0.72, 90: 0.7, 92: 0.72})
    assert not leg_clear(beside, 5.0, 0.0)


def test_open_flanks_and_the_airframe_itself_do_not_refuse_a_leg():
    from mission_bt.banner_orbit import leg_clear
    assert leg_clear(_scan_mav({90: 2.0, 270: 1.5}), 5.0, 0.0)
    assert leg_clear(_scan_mav({180: 0.22, 151: 0.35}), 5.0, 0.0), "mast and arms"


# ---- a GROUND pass backs away from green it cannot identify ------------- #

def test_the_ground_pass_backs_away_from_cut_green_before_orbiting():
    import math
    from mission_bt.mission_tree import AlignToBanner
    mav = MagicMock()
    mav.pos.return_value = (1.0, -0.5, 5.0)
    leaf = AlignToBanner(mav, clock=lambda: 0.0, search_camera_pose="GROUND")
    leaf._green = {"x": 6.0, "y": -3.0, "range": 5.6, "heading": math.radians(-30),
                   "source": "camera", "cut": True}
    leaf._restart_sweep_at = MagicMock(return_value="moving")
    assert leaf._next_orbit_vantage(5.0) == "moving"
    (nx, ny, nz, hd), _ = leaf._restart_sweep_at.call_args
    assert math.hypot(nx - 1.0, ny + 0.5) == pytest.approx(3.0)
    assert (nx - 1.0) < 0 < (ny + 0.5), "away from the green, not round it"
    assert nz == 5.0
    leaf._next_orbit_vantage(5.0)
    leaf._restart_sweep_at.reset_mock()
    assert leaf._ground_backoff(5.0) is None, "bounded: two back-offs"


def test_a_hung_pass_does_not_back_off():
    from mission_bt.mission_tree import AlignToBanner
    leaf = AlignToBanner(MagicMock(), clock=lambda: 0.0)
    leaf._green = {"x": 6.0, "y": -3.0, "range": 5.6, "heading": 0.0, "source": "camera"}
    assert leaf._ground_backoff(5.0) is None


# ---- the return gate's zone side, whatever gap the venue leaves --------- #

def _finder(gate_heading=0.0):
    from mission_bt.mission_tree import FindReturnBanner
    mav = MagicMock()
    mav.gate_heading = gate_heading
    mav.outbound_banner_xy = (0.0, 0.0)
    # The zone starts 9 m beyond the 10 m corridors.
    mav.delivery_search_zone = lambda c: (19.0 + c, 59.0 - c, -15.0 + c, 15.0 - c)  # c<0 grows it
    return FindReturnBanner(mav, alt=5.0, clock=lambda: 0.0, corridor_length_m=10.0)


def test_a_stand_off_beyond_the_corridors_is_the_zone_side_however_far_the_zone():
    f = _finder()
    assert f._zone_side(15.0, -4.0), "5 m past the return entrance"
    assert not f._zone_side(5.0, -4.0), "inside the return lane is its back"


def test_without_the_outbound_axis_the_zone_box_still_decides():
    f = _finder()
    f.mav.gate_heading = None
    assert not f._zone_side(15.0, -4.0)
    assert f._zone_side(17.0, -4.0)


# ---- a laid return banner is looked at from where it is in frame -------- #

def test_the_return_search_stands_farther_off_a_ground_mounted_gate():
    f = _finder()
    assert f._standoff() == f.standoff_m
    f.mav.banner_placement_learned = "ground"
    assert f._standoff() >= 7.5


def test_a_ground_pass_relocates_back_along_the_bearing():
    import math
    from mission_bt.mission_tree import AlignToBanner
    mav = MagicMock()
    mav.pos.return_value = (20.0, -6.0, 5.0)
    mav.yaw.return_value = math.pi
    leaf = AlignToBanner(mav, clock=lambda: 0.0, search_camera_pose="GROUND")
    leaf._seen_yaw = math.pi                 # facing the gate, -x
    leaf._restart_sweep_at = MagicMock(return_value="moving")
    leaf._relocate("nothing in view")
    (nx, ny, nz, _), _ = leaf._restart_sweep_at.call_args
    assert nx > 20.0, "stepped back, away from the sheet"


def test_a_far_laid_sheet_is_closed_in_on_while_descending_to_square_up():
    import math
    from mission_bt.mission_tree import AlignToBanner
    mav = MagicMock()
    mav.pos.return_value = (23.2, -6.8, 5.0)
    mav.yaw.return_value = math.pi
    leaf = AlignToBanner(mav, clock=lambda: 0.0, search_camera_pose="GROUND",
                         alt_floor_m=2.4384)
    leaf.ground_range = lambda: 7.5
    leaf._begin_square()
    ax, ay, az = leaf._anchor
    target = 0.5 * (leaf.min_standoff + leaf.max_standoff)
    assert 23.2 - ax == pytest.approx(7.5 - target)
    assert az == pytest.approx(2.4384)


# ---- a laid square-up measures past the mouth, widest face first -------- #

def test_past_the_mouth_the_widest_face_wins_over_a_stub_of_wall_end():
    import math
    from mission_bt.scan_geometry import fit_surface
    inc = math.radians(1.0)
    n = 360
    ranges = [float("inf")] * n
    a0 = -math.pi

    def put(deg, r):
        ranges[int(round((math.radians(deg) - a0) / inc)) % n] = r

    # A stub of wall end, 0.4 m of it, at 5.6 m on the left...
    for k, deg in enumerate(range(-26, -22)):
        put(deg, 5.6 + 0.1 * k)
    # ...and a 1.6 m obstacle face square across the lane at 6.2 m.
    for deg in range(-1, 15):
        put(deg, 6.2 / math.cos(math.radians(deg)))
    near = fit_surface(a0, inc, ranges, 0.0, math.radians(35))
    assert not near["ok"]
    far = fit_surface(a0, inc, ranges, 0.0, math.radians(35),
                      min_range_m=5.0, widest_first=True)
    assert far["ok"] and far["range_m"] == pytest.approx(6.2, abs=0.05)
    assert abs(far["angle_rad"]) < math.radians(2.0)
