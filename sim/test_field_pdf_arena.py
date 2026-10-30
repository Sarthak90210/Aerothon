#!/usr/bin/env python3
"""The organisers' Track 1 field (PDF, 23 Oct 2026), entered at the GCS.

What the PDF changed against the earlier clarifications, each as a check:

    * the exit corridor is marked with BLUE boards (#0000FF), the entry one
      green (#00B140), and there are no orange no-entry boards: the return
      lap looks for the exit shade, and orange is no longer required;
    * arch boards 11.5 x 1.5 ft, ground boards 11.5 x 1 ft, 1 in borders;
    * QR 1 m with no white border;
    * three 6 ft boards in the exit corridor: a navigation height that puts
      the lidar plane over them is refused at the GCS.

    python3 -m pytest sim/test_field_pdf_arena.py -v
"""
import json
import math
import os
import re
import subprocess
import sys
import types
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src/aerothon_mission/mission_bt"))

from mission_bt import arena_dimensions as A                  # noqa: E402
from perception_banner import colours                         # noqa: E402
from perception_banner.banner_node import BannerNode          # noqa: E402
import world_spec as W                                        # noqa: E402
import field_pdf_world                                        # noqa: E402
import organiser_inputs                                       # noqa: E402

FT, INCH = 0.3048, 0.0254
PRESET = "AeroTHON 2026 Track 1 field (organiser PDF)"
FIELD = {"green": "#00B140", "exit": "#0000FF", "red": "#FF0000"}


# ---- the GCS preset ------------------------------------------------------ #

def test_the_preset_carries_the_pdf_dimensions():
    d = A.validate(A.BUILTIN_PRESETS[PRESET])
    c, b = d["corridor"], d["banner"]
    assert c["length_m"] == pytest.approx(22 * FT)
    assert c["width_m"] == pytest.approx(11.5 * FT)
    assert c["wall_height_m"] == pytest.approx(10 * FT)
    assert (b["width_m"], b["height_m"], b["ground_height_m"]) == pytest.approx(
        (11.5 * FT, 1.5 * FT, 1 * FT))
    assert b["suspended_bottom_m"] == pytest.approx(8 * FT)        # hung down to 8 ft
    assert b["border_m"] == pytest.approx(INCH) and b["placement"] == "both"
    # The venue's tag boards (29 Oct) have a white margin; the PDF said none.
    assert (d["qr"]["target_m"], d["qr"]["start_m"], d["qr"]["border_m"]) == (1.0, 1.0, 0.1)
    assert (d["red_zone"]["side_m"], d["red_zone"]["border_m"]) == pytest.approx((10 * FT, INCH))
    assert d["obstacle"]["height_m"] == pytest.approx(6 * FT)
    assert d["obstacle"]["reach_frac"] * c["width_m"] == pytest.approx(3.5 * FT, abs=1e-3)
    assert (d["payload"]["length_m"], d["payload"]["width_m"], d["payload"]["mass_kg"]) == (
        0.10, 0.05, 0.10)


def test_a_navigation_height_over_the_6ft_boards_is_refused_with_the_fix():
    dims = json.loads(json.dumps(A.BUILTIN_PRESETS[PRESET]))
    dims["corridor"]["nav_height_m"] = 8 * FT
    with pytest.raises(ValueError, match="would not see them.*1.65 m or less"):
        A.validate(dims)
    dims["corridor"]["nav_height_m"] = 1.64
    A.validate(dims)


def test_presets_saved_before_the_new_fields_keep_their_arena():
    old = {"banner": {"height_m": 0.5}, "corridor": {"wall_height_m": 3.2, "nav_height_m": 2.5}}
    d = A.validate(old)
    assert d["banner"]["ground_height_m"] == 0.5
    assert d["obstacle"]["height_m"] == pytest.approx(0.95 * 3.2)


def test_the_gcs_form_holds_the_same_obstacle_rule():
    text = (ROOT / "src/aerothon_gcs/tauri_app/src/arenaForm.ts").read_text(encoding="utf-8")
    assert "0.0815" in text and "obstacle?.height_m" in text
    schema = json.loads((ROOT / "src/aerothon_gcs/tauri_app/src/arenaSchema.json").read_text())
    assert PRESET in schema["presets"]
    assert {("banner", "ground_height_m"), ("obstacle", "height_m")} <= {
        (f["group"], f["key"]) for f in schema["fields"]}


# ---- which colours are required, and which banner each lap looks for ---- #

def test_the_field_colours_are_complete_without_orange():
    assert colours.missing(FIELD) == []
    assert colours.missing({"green": "#07A03D", "orange": "#EB5A0A", "red": "#C4161C"}) == []
    assert colours.missing({"green": "#00B140", "red": "#FF0000"}) == ["exit (or orange)"]
    assert colours.missing({"exit": "#0000FF"}) == ["green", "red"]
    assert colours.validate(FIELD) == FIELD


def _patch(hex_code):
    bgr = np.full((8, 8, 3), colours.parse_hex(hex_code)[::-1], np.uint8)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)


def test_the_return_lap_searches_the_exit_blue_and_never_green():
    node = types.SimpleNamespace(_colours=dict(FIELD), _target="exit")
    bands = BannerNode.colour_ranges(node)
    assert colours.mask(_patch("#0000FF"), bands).all()
    assert not colours.mask(_patch("#00B140"), bands).any()
    node._target = "green"
    bands = BannerNode.colour_ranges(node)
    assert colours.mask(_patch("#00B140"), bands).all()
    assert not colours.mask(_patch("#0000FF"), bands).any()


def test_without_an_exit_shade_the_return_lap_keeps_the_rulebook_green():
    rulebook = {"green": "#07A03D", "orange": "#EB5A0A", "red": "#C4161C"}
    node = types.SimpleNamespace(_colours=rulebook, _target="exit")
    bands = BannerNode.colour_ranges(node)
    assert colours.mask(_patch("#07A03D"), bands).all()
    assert not colours.mask(_patch("#EB5A0A"), bands).any()


def test_a_blue_panel_is_named_exit():
    node = types.SimpleNamespace(_colours=dict(FIELD))
    node.colour_ranges = lambda name=None: BannerNode.colour_ranges(node, name)
    panel = np.full((20, 40, 3), colours.parse_hex("#0000FF")[::-1], np.uint8)
    assert BannerNode.dominant_colour(node, panel)[0] == "exit"


def test_the_mission_switches_the_banner_lap_by_lap():
    from mission_bt.mission_tree import build_root
    from unittest.mock import MagicMock
    from test_fail_closed_stages import FakeMav
    params = {'takeoff_alt': 5.0, 'search_alt': 10.0, 'drop_alt': 5.0,
              'image_width_px': 1280, 'image_height_px': 720, 'camera_hfov': 1.0472,
              'target_marker_m': 2.2, 'px_per_module_floor': 5.3, 'lane_overlap': 0.30,
              'zone_boundary_clearance': 1.0, 'corridor_alt': 3.0, 'scan_floor_alt': 2.0,
              'land_commit_alt': 1.5, 'banner_sweep_limit': math.pi}
    root = build_root(FakeMav(), MagicMock(), params)
    mission = [c for c in root.children if c.name == "Mission"][0]
    names = [n.name for n in mission.iterate()]
    at = names.index
    assert at("BannerTargetOutbound") < at("CameraNadirForQR")
    assert at("ReturnToCorridorMouth") < at("BannerTargetReturn") < at("CameraBannerReturn")
    assert at("BannerTargetReturn") < names.index("ReturnCorridor") < at("BannerTargetHome")
    leaf = [n for n in mission.iterate() if n.name == "BannerTargetReturn"][0]
    assert leaf.lap == "exit"


def test_the_return_gate_is_searched_for_at_the_entry_lineup_height():
    """Field world run 1: entry banner squared up at 2.58 m, the return
    search then flown at the 1.5 m navigation height, the board's top out
    of a level camera's frame at the stand-off, and no identification."""
    from mission_bt.mission_tree import build_root
    from unittest.mock import MagicMock
    from test_fail_closed_stages import FakeMav
    params = {'takeoff_alt': 5.0, 'search_alt': 10.0, 'drop_alt': 5.0,
              'image_width_px': 1280, 'image_height_px': 720, 'camera_hfov': 1.0472,
              'target_marker_m': 2.2, 'px_per_module_floor': 5.3, 'lane_overlap': 0.30,
              'zone_boundary_clearance': 1.0, 'corridor_alt': 1.5, 'scan_floor_alt': 2.0,
              'land_commit_alt': 1.5, 'banner_sweep_limit': math.pi}
    mav = FakeMav()
    root = build_root(mav, MagicMock(), params)
    leaves = {n.name: n for n in root.iterate()}
    descend, search = leaves["DescendToReturnIdent"], leaves["FindReturnBanner"]
    assert descend.target_alt() == 1.5 and search.search_alt() == 1.5      # nothing measured yet
    mav.banner_lineup_alt = 2.58
    assert descend.target_alt() == pytest.approx(2.58) and search.search_alt() == pytest.approx(2.58)
    mav.banner_lineup_alt = 14.0
    assert search.search_alt() == 10.0                                      # never above search height
    mav.banner_lineup_alt = 0.8
    assert search.search_alt() == 1.5                                       # nor under the corridor


def test_the_component_banner_test_looks_for_the_entry_banner():
    text = (ROOT / "src/aerothon_runtime/aerothon_runtime/execution_node.py").read_text(
        encoding="utf-8")
    start = text.index("elif task == 'banner':")
    assert "SetBannerTarget('BannerTargetTest',mav,'green')" in text[start:start + 400]


def test_the_commander_refuses_an_unknown_lap():
    from mission_bt.mav_commander import Mav
    sent = []
    fake = types.SimpleNamespace(pub_banner_target=types.SimpleNamespace(publish=sent.append))
    Mav.set_banner_target(fake, "exit")
    assert fake.banner_target == "exit" and sent[-1].data == "exit"
    with pytest.raises(ValueError):
        Mav.set_banner_target(fake, "orange")


def test_the_gcs_offers_the_exit_banner_and_drops_blank_shades():
    app = (ROOT / "src/aerothon_gcs/tauri_app/src/App.tsx").read_text(encoding="utf-8")
    assert '["green", "exit", "orange", "red"]' in app
    assert "suppliedColours(colours)" in app and "coloursReady(colours)" in app


# ---- the 1 inch border on an 11.5 x 1.5 ft board --------------------------- #

@pytest.fixture
def detector():
    import rclpy
    from rclpy.parameter import Parameter
    owns = not rclpy.ok()
    if owns:
        rclpy.init()
    node = BannerNode()
    node._colours = dict(FIELD)
    node._target = "exit"
    node.set_parameters([Parameter("banner_width_m", value=11.5 * FT),
                         Parameter("banner_height_m", value=1.5 * FT)])
    node.gate.open = lambda: True
    node.sent, node.details = [], []
    node.pub.publish = node.sent.append
    node.pub_detail.publish = node.details.append
    node.pub_annot.publish = lambda m: None
    yield node
    node.destroy_node()
    if owns and rclpy.ok():
        rclpy.shutdown()


def _exit_board(blue=(186, 0, 0), white=(245, 245, 245)):
    """The exit board as the return search sees it from the stand-off (field
    world run 1's frames): pale sky above, the shaded lane below, the lane's
    grey walls hard against both ends -- the board is the lane's width -- and
    a 540 x 70 px panel whose 1 inch border is 4 px (70 px x 1 in / 1.5 ft)."""
    img = np.full((540, 960, 3), (70, 72, 74), np.uint8)       # shaded lane
    img[:150] = (248, 228, 220)                                 # pale sky (BGR)
    x, y, w, h, t = 210, 160, 540, 70, 4
    img[150:, x - t - 70:x - t] = (124, 124, 124)               # walls
    img[150:, x + w + t:x + w + t + 70] = (124, 124, 124)
    cv2.rectangle(img, (x - t, y - t), (x + w + t - 1, y + h + t - 1), white, -1)
    cv2.rectangle(img, (x, y), (x + w - 1, y + h - 1), blue, -1)
    return img


def _feed(node, img, stamp):
    from cv_bridge import CvBridge
    msg = CvBridge().cv2_to_imgmsg(img, encoding="bgr8")
    msg.header.stamp.sec = stamp
    node.on_image(msg)
    return json.loads(node.details[-1].data)


def test_a_one_inch_border_needs_the_gcs_border_width(detector):
    img = _exit_board()
    d = _feed(detector, img, 10)
    assert not d["identified"], "the 3-inch ring should not find a 1-inch border"
    detector.border_m = 1 * INCH                  # what the applied dimensions carry
    d = _feed(detector, img, 11)
    assert d["identified"], d.get("reason")


def test_the_applied_dimensions_carry_the_border_to_the_detector(detector):
    from std_msgs.msg import String
    dims = A.validate(A.BUILTIN_PRESETS[PRESET])
    detector._on_arena_dimensions(String(data=json.dumps({"applied": True, "dimensions": dims})))
    assert detector.border_m == pytest.approx(INCH)
    assert detector._border_ring_px((0, 0, 540, 70)) == 5


def test_a_full_brightness_blue_print_still_shows_its_white_border(detector):
    """#0000FF in sun reaches V 255: nothing can be 8% brighter."""
    detector.border_m = 1 * INCH
    d = _feed(detector, _exit_board(blue=(255, 0, 0), white=(240, 240, 240)), 20)
    assert d["identified"], d.get("reason")


@pytest.mark.parametrize("name", ["exit_board_field_pdf_frontal.jpg",
                                  "exit_board_field_pdf_clipped.jpg"])
def test_the_rendered_exit_board_is_identified_with_its_ends_at_the_walls(detector, name):
    """Field world run 2's own return-search frames (copied to tests/fixtures):
    the board's long sides framed, its ends flush with the lane walls."""
    from rclpy.parameter import Parameter
    detector.set_parameters([Parameter("camera_hfov", value=0.851919)])
    detector.border_m = 1 * INCH
    d = _feed(detector, cv2.imread(str(ROOT / "tests/fixtures" / name)), 40)
    assert d["identified"], d.get("reason")


def test_a_wide_panel_framed_on_one_long_side_only_is_refused(detector):
    """Ends at the walls and no bottom border: only the top is framed. (One
    dark edge with the other three framed is the outline test's shadow
    allowance, which predates the wall-end rule.)"""
    detector.border_m = 1 * INCH
    img = _exit_board()
    img[230:242, 150:820] = (70, 72, 74)                         # no bottom border (rows 230-233)
    img[150:, 136:210] = (124, 124, 124)                         # ends flush with the walls
    img[150:, 750:824] = (124, 124, 124)
    d = _feed(detector, img, 50)
    assert not d["identified"], d


def test_a_wide_panel_framed_only_at_its_ends_is_refused(detector):
    """The corridor floor between two white walls: framed on its ends."""
    detector.border_m = 1 * INCH
    img = np.full((540, 960, 3), (70, 72, 74), np.uint8)
    cv2.rectangle(img, (206, 160), (209, 229), (245, 245, 245), -1)
    cv2.rectangle(img, (750, 160), (753, 229), (245, 245, 245), -1)
    cv2.rectangle(img, (210, 160), (749, 229), (186, 0, 0), -1)
    d = _feed(detector, img, 60)
    assert not d["identified"], d


def test_green_is_never_taken_on_the_return_lap(detector):
    detector.border_m = 1 * INCH
    d = _feed(detector, _exit_board(blue=(64, 177, 0)), 30)     # the entry green
    assert not d["identified"]


# ---- QR codes with no white border ----------------------------------------- #

def _fixture(name):
    return cv2.imread(str(ROOT / "tests/fixtures" / name))


def test_a_borderless_start_code_on_the_pad_is_read():
    """Field world run 4's start scan: zbar read none of 39 frames as they
    came (no light quiet zone between the code and the grey-157 pad)."""
    from perception_qr.qr_decode import QrDecoder
    found, located = QrDecoder().read(_fixture("start_qr_borderless_on_pad.jpg"))
    assert [p for p, _ in found] == ["AEROTHON2026:M2:TARGET_C"], located


def test_the_borderless_start_pattern_matches_its_pad_from_10m_and_no_other():
    from perception_qr import qr_appearance as QA
    from perception_qr.qr_decode import QrDecoder
    dec = QrDecoder()

    def sig(name):
        img = _fixture(name)
        found, located = dec.read(img)
        return QA.signature(img, found[0][1] if found else located)

    start = sig("start_qr_borderless_on_pad.jpg")
    assert (start.kind, start.n) == ("modules", 25)
    same, score = QA.same_marker(start, sig("pad_c_borderless_10m.jpg"))
    assert same, score
    other, score = QA.same_marker(start, sig("pad_d_borderless_10m.jpg"))
    assert not other, score


def test_a_start_marker_running_off_the_frame_is_never_the_reference():
    import rclpy
    from perception_qr.qr_decode import QrDecoder
    from perception_qr.qr_node import QrNode
    owns = not rclpy.ok()
    if owns:
        rclpy.init()
    from rclpy.parameter import Parameter
    node = QrNode()
    node.set_parameters([Parameter("marker_kind", value="qr")])
    try:
        node.target = ""
        img = _fixture("start_qr_borderless_clipped.jpg")
        found, located = QrDecoder().read(img)
        quad = found[0][1] if found else located
        assert quad is not None and (quad.min() < 0 or quad[:, 1].max() > img.shape[0]
                                     or quad[:, 0].max() > img.shape[1]), "fixture is not clipped"
        node._appearance(img, quad, node._marker_px(quad))
        assert node._reference is None
        img = _fixture("start_qr_borderless_on_pad.jpg")
        found, _ = QrDecoder().read(img)
        node._appearance(img, found[0][1], node._marker_px(found[0][1]))
        assert node._reference is not None and node._reference.kind == "modules"
    finally:
        node.destroy_node()
        if owns and rclpy.ok():
            rclpy.shutdown()


# ---- the simulated field --------------------------------------------------- #

@pytest.fixture(scope="module")
def field():
    spec = W.normalise(field_pdf_world.build("aerothon26_field", "c"))
    errs, warns = W.validate(spec)
    assert errs == [], errs
    return spec


def test_the_field_world_flies_its_corridors_at_the_navigation_height(field):
    assert W.corridor_alt(field) == pytest.approx(1.5)
    plane = W.corridor_alt(field) + W.LIDAR_ABOVE_BODY_M
    assert plane < min(o["h"] for o in field["return_corridor"]["obstacles"]) - 0.1


def test_the_old_duck_altitude_would_have_hidden_the_boards(field):
    """Ducked 0.6 m under the 8 ft edge, the scan plane is over 6 ft."""
    ducked = max(W.DUCK_FLOOR_M, 8 * FT - W.LIDAR_ABOVE_BODY_M - W.DUCK_MARGIN_M)
    assert ducked + W.LIDAR_ABOVE_BODY_M > 6 * FT


def test_the_field_world_has_three_6ft_boards_across_3_5ft(field):
    obstacles = field["return_corridor"]["obstacles"]
    assert len(obstacles) == 3
    for o in obstacles:
        assert (o["d"], o["h"]) == pytest.approx((3.5 * FT, 6 * FT), abs=1e-3)
    assert [math.copysign(1, o["v"]) for o in obstacles] == [1, -1, 1]


def test_the_field_world_prints_the_pdf_boards(tmp_path, field):
    spec_path = tmp_path / "field.json"
    spec_path.write_text(json.dumps(field))
    out = tmp_path / "field.sdf"
    subprocess.run([sys.executable, str(ROOT / "scripts/materialize_world.py"),
                    "--source", str(ROOT / "src/aerothon_sim/sim_gazebo/worlds/mission2.sdf"),
                    "--assets", str(ROOT / "src/aerothon_sim/sim_gazebo/materials"),
                    "--output", str(out), "--world-spec", str(spec_path)],
                   check=True, capture_output=True, text=True)
    world = out.read_text()

    def model(name):
        i = world.index(f'<model name="{name}"')
        return world[i:world.index("</model>", i)]

    blue, green = "0.000 0.000 1.000 1", "0.000 0.694 0.251 1"
    assert blue in model("return_aerothon_banner") and green not in model("return_aerothon_banner")
    assert green in model("forward_aerothon_banner") and blue not in model("forward_aerothon_banner")
    assert blue in model("corridor_return") and green in model("corridor_outbound")
    assert "orange_banner" not in world                     # no no-entry boards
    hung = model("forward_aerothon_banner")
    assert f"<size>0.12 {11.5 * FT:.4f} {1.5 * FT:.4f}</size>" in hung
    assert f"<size>0.022 {11.5 * FT:.4f} {INCH:.4f}</size>" in hung        # 1 in border
    laid = model("corridor_outbound")
    assert f"<size>{1 * FT:.3f} {11.5 * FT:.3f} 0.008</size>" in laid       # 1 ft ground board
    # The exit board lies on the zone, which begins at the exit corridor's
    # mouth: drawn on the slab, not under it (run 3); the entry one on the ground.
    assert re.search(r'name="ground_banner_panel"><pose>[-0-9.]+ 0 0\.102 0 0 0</pose>', model("corridor_return"))
    assert re.search(r'name="ground_banner_panel"><pose>[-0-9.]+ 0 0\.012 0 0 0</pose>', laid)
    qr = model("delivery_qr_target_c")
    # The venue's board (29 Oct): a 1 m white plate, a 0.1 m margin, the
    # AprilTag's 8 cells 0.1 m each, its black top row the full 0.8 m.
    assert "<size>1.0 1.0 0.04</size>" in qr
    assert "<size>0.800000 0.100000 0.012</size>" in qr
    assert re.search(r'<pose>0\.000000 0\.350000 0\.026', qr), "tag border not inside the margin"
    assert not re.findall(r"@[A-Z_]+@", world)


def test_organiser_inputs_send_no_orange_for_the_field(field):
    out = organiser_inputs.organiser_inputs(field, 12.97, 79.16)
    assert out["banner_colours"] == FIELD
