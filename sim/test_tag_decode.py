#!/usr/bin/env python3
"""The field's AprilTag 36h11 boards: read, matched, and printed in the world.

The venue's markers (photographed 29 Oct 2026) are AprilTag 36h11 tags, not
QR codes. These pin that the photographs themselves read to the IDs on the
boards, that a flat-shaded rendered board reads at every size the search
sees, that the node matches a pad by its ID alone, and that the simulator
prints the tags the detector reads.

    source /opt/ros/jazzy/setup.bash
    python3 -m pytest sim/test_tag_decode.py -v
"""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for pkg in (("aerothon_perception", "camera_ctrl"),
            ("aerothon_perception", "perception_qr")):
    sys.path.insert(0, os.path.join(ROOT, "src", *pkg))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cv2                                                  # noqa: E402
import numpy as np                                          # noqa: E402

from perception_qr import tag_decode as T                   # noqa: E402
from perception_qr.qr_match import APPEARANCE_ONLY, same_tag  # noqa: E402

FIELD = os.path.join(ROOT, "tests", "perception", "field_tags_20261029")
GREY = (60, 110, 157, 200)       # dark grass .. the grey take-off pad .. light slab


def board(tag_id, px, angle=0.0, ground=110, margin=0.1, w=960, h=540):
    """A tag `px` wide on a white board, flat-shaded as Gazebo renders it."""
    cells = np.array(T.marker_cells(T.DEFAULT_DICTIONARY, tag_id))
    tag = cv2.resize(np.where(cells, 20, 235).astype(np.uint8), (px, px),
                     interpolation=cv2.INTER_NEAREST)
    m = max(1, int(round(px * margin / (1 - 2 * margin))))
    sheet = cv2.copyMakeBorder(tag, m, m, m, m, cv2.BORDER_CONSTANT, value=235)
    img = np.full((h, w), ground, np.uint8)
    y, x = h // 2 - sheet.shape[0] // 2, w // 2 - sheet.shape[1] // 2
    img[y:y + sheet.shape[0], x:x + sheet.shape[1]] = sheet
    rot = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.cvtColor(cv2.warpAffine(img, rot, (w, h), borderValue=ground),
                        cv2.COLOR_GRAY2BGR)


@unittest.skipUnless(T.available(), "OpenCV without the aruco module")
class FieldPhotographTests(unittest.TestCase):
    """The boards at the venue, cropped from the operator's photographs."""

    def test_every_photographed_board_reads_its_id(self):
        expected = json.load(open(os.path.join(FIELD, "expected.json")))
        self.assertEqual(sorted(set(expected.values())), [100, 200, 300, 400, 500])
        dec = T.TagDecoder()
        for name, tag_id in expected.items():
            found, _ = dec.read(cv2.imread(os.path.join(FIELD, name)))
            self.assertIn(str(tag_id), [p for p, _ in found], name)

    def test_the_photographs_are_no_other_family(self):
        # A 4x4 or 6x6 ArUco dictionary reads nothing board-sized in them.
        for other in ("DICT_4X4_1000", "DICT_6X6_1000", "DICT_ARUCO_ORIGINAL"):
            dec = T.TagDecoder(other)
            for name in json.load(open(os.path.join(FIELD, "expected.json"))):
                img = cv2.imread(os.path.join(FIELD, name))
                for _, quad in dec.read(img)[0]:
                    self.assertLess(float(np.ptp(quad, axis=0).max()), 0.2 * max(img.shape),
                                    f"{other} read a board in {name}")


@unittest.skipUnless(T.available(), "OpenCV without the aruco module")
class RenderedBoardTests(unittest.TestCase):

    def setUp(self):
        self.dec = T.TagDecoder()

    def test_a_flat_board_reads_at_every_size_turn_and_ground(self):
        # OpenCV's default candidate distance dropped 48 of these: the dark
        # band round a white board was kept and the tag inside it was not.
        missed = []
        for ground in GREY:
            for px in (24, 40, 64, 100, 160, 240, 360):
                for angle in (0, 17, 45, 80):
                    found, _ = self.dec.read(board(300, px, angle, ground))
                    if [p for p, _ in found] != ["300"]:
                        missed.append((ground, px, angle, [p for p, _ in found]))
        self.assertEqual(missed, [])

    def test_each_tag_reads_once_with_its_own_corners(self):
        found, unread = self.dec.read(board(200, 160, 17))
        self.assertIsNone(unread)
        self.assertEqual(len(found), 1)
        payload, quad = found[0]
        self.assertEqual(payload, "200")
        self.assertEqual(quad.shape, (4, 2))
        self.assertLess(np.linalg.norm(quad.mean(axis=0) - (480, 270)), 2.0)
        side = np.linalg.norm(np.roll(quad, -1, axis=0) - quad, axis=1)
        self.assertTrue(np.all(np.abs(side - 160) < 6), side)

    def test_two_boards_in_one_frame_both_read(self):
        img = np.full((540, 960, 3), 110, np.uint8)
        img[:, :480] = board(100, 120, 10, w=480)
        img[:, 480:] = board(500, 120, -30, w=480)
        self.assertEqual(sorted(p for p, _ in self.dec.read(img)[0]), ["100", "500"])

    def test_motion_blur_up_to_a_fifth_of_the_tag_still_reads(self):
        for px, k in ((64, 9), (100, 15), (160, 21)):
            ker = np.zeros((k, k), np.float32)
            ker[k // 2, :] = 1.0 / k
            found, _ = self.dec.read(cv2.filter2D(board(400, px, 17), -1, ker))
            self.assertEqual([p for p, _ in found], ["400"], (px, k))

    def test_ground_textures_read_as_nothing(self):
        rng = np.random.default_rng(1)
        for t in range(30):
            g = rng.normal(120, 35, (540, 960)).clip(0, 255).astype(np.uint8)
            g = cv2.GaussianBlur(g, (0, 0), rng.uniform(1, 6))
            if t % 2:                 # paving: light and dark slabs, dark joints
                g[:] = 150
                for y in range(0, 540, 45):
                    for x in range(0, 960, 90):
                        g[y + 3:y + 42, x + 3:x + 87] = int(rng.choice([95, 130, 165, 185]))
            found, unread = self.dec.read(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR))
            self.assertEqual((found, unread), ([], None), t)

    def test_cells_are_an_eight_cell_tag_with_a_black_border(self):
        cells = np.array(T.marker_cells(T.DEFAULT_DICTIONARY, 100))
        self.assertEqual(cells.shape, (8, 8))
        self.assertTrue(cells[0].all() and cells[-1].all()
                        and cells[:, 0].all() and cells[:, -1].all())
        self.assertNotEqual(T.marker_cells(T.DEFAULT_DICTIONARY, 100),
                            T.marker_cells(T.DEFAULT_DICTIONARY, 200))

    def test_an_unknown_dictionary_is_refused(self):
        with self.assertRaises(ValueError):
            T.TagDecoder("DICT_NOT_A_FAMILY")
        self.assertEqual(T.TagDecoder("dict_apriltag_36H11").name, "dict_apriltag_36H11")


class SameTagTests(unittest.TestCase):

    def test_a_pad_matches_only_the_start_tags_id(self):
        self.assertTrue(same_tag("300", "300"))
        self.assertTrue(same_tag("ID 300", "300"))
        self.assertTrue(same_tag("0300", "300"))
        for other in ("30", "3000", "200", "", "300 200"):
            self.assertFalse(same_tag("300", other), other)
        self.assertFalse(same_tag("", "300"))
        self.assertFalse(same_tag(APPEARANCE_ONLY, "300"))


@unittest.skipUnless(T.available(), "OpenCV without the aruco module")
class TagNodeTests(unittest.TestCase):
    """The node as the mission sees it, on the default (tag) markers."""

    @classmethod
    def setUpClass(cls):
        import rclpy
        if not rclpy.ok():
            rclpy.init()

    @classmethod
    def tearDownClass(cls):
        import rclpy
        if rclpy.ok():
            rclpy.shutdown()

    def setUp(self):
        from cv_bridge import CvBridge
        from perception_qr.qr_node import QrNode
        self.bridge = CvBridge()
        self.node = QrNode()
        self.detail, self.offsets = [], []
        self.node.pub_detail.publish = lambda m: self.detail.append(json.loads(m.data))
        self.node.pub_offset.publish = self.offsets.append
        for pub in (self.node.pub_matched, self.node.pub_decoded, self.node.pub_annot):
            pub.publish = lambda m: None
        self.stamp = 1.0

    def tearDown(self):
        self.node.destroy_node()

    def see(self, img):
        message = self.bridge.cv2_to_imgmsg(img, "bgr8")
        message.header.stamp.sec = int(self.stamp)
        self.stamp += 1.0
        self.node.on_image(message)
        return self.detail[-1]

    def target(self, value):
        from std_msgs.msg import String
        self.node.on_target(String(data=value))

    def test_the_start_tag_names_the_pad_with_its_id(self):
        self.target("")
        start = self.see(board(300, 200))
        self.assertEqual((start["accepted"], start["matched"]), ("300", False))
        self.assertEqual(start["marker_kind"], "aruco")
        self.assertEqual(start["marker_dictionary"], "DICT_APRILTAG_36h11")
        # No QR pattern reference: the mission's appearance-only fallback,
        # which needs a module grid, can never stand in for a tag's ID.
        self.assertFalse(start["reference_captured"])
        self.assertIsNone(start["reference_kind"])
        self.assertEqual(self.offsets[-1].z, 0.5)
        self.target("300")
        pad = self.see(board(300, 120, 45))
        self.assertTrue(pad["matched"])
        self.assertEqual(pad["match_basis"], ["payload"])
        self.assertEqual(self.offsets[-1].z, 1.0)
        for other in (100, 200, 400, 500):
            self.assertFalse(self.see(board(other, 120, 30))["matched"], other)

    def test_ignoring_payloads_does_not_discard_tag_ids(self):
        from rclpy.parameter import Parameter
        self.node.set_parameters([Parameter("use_payloads", value=False)])
        self.target("500")
        self.assertTrue(self.see(board(500, 120))["matched"])

    def test_qr_markers_remain_selectable(self):
        from rclpy.parameter import Parameter
        self.node.set_parameters([Parameter("marker_kind", value="qr")])
        self.target("")
        self.assertEqual(self.see(board(300, 200))["accepted"], "")
        if hasattr(cv2, "QRCodeEncoder"):
            code = cv2.QRCodeEncoder.create().encode("PAD 3")
            code = cv2.resize(code, (200, 200), interpolation=cv2.INTER_NEAREST)
            img = np.full((540, 960), 110, np.uint8)
            img[150:390, 360:600] = cv2.copyMakeBorder(code, 20, 20, 20, 20,
                                                       cv2.BORDER_CONSTANT, value=255)
            got = self.see(cv2.cvtColor(img, cv2.COLOR_GRAY2BGR))
            self.assertEqual((got["accepted"], got["marker_kind"]), ("PAD 3", "qr"))


class WorldMarkerTests(unittest.TestCase):
    """The simulator prints the tags the detector reads."""

    def test_field_worlds_print_the_photographed_ids(self):
        import world_spec as W
        for name in ("aerothon26_field", "aerothon26_field_L10",
                     "aerothon26_field_red_by_c", "aerothon26_field_red_near_c"):
            spec = W.load(os.path.join(ROOT, "sim", "worlds", name + ".json"))
            self.assertEqual(W.validate(spec)[0], [], name)
            self.assertEqual(spec["qr"]["kind"], "apriltag_36h11")
            self.assertEqual(spec["qr"]["ids"], W.DEFAULT_TAG_IDS)
            self.assertAlmostEqual(spec["qr"]["border_m"], 0.1)

    def test_tag_ids_are_checked(self):
        import world_spec as W
        spec = W.load(os.path.join(ROOT, "sim", "worlds", "aerothon26_field.json"))
        for ids, why in (({"a": 1, "b": 1, "c": 2, "d": 3, "e": 4}, "own tag ID"),
                         ({"a": 1, "b": 2, "c": 3, "d": 4}, "integer for each"),
                         ({"a": 1, "b": 2, "c": 3, "d": 4, "e": 999}, "0-586")):
            bad = dict(spec, qr=dict(spec["qr"], ids=ids))
            self.assertTrue(any(why in e for e in W.validate(bad)[0]), ids)
        bad = dict(spec, qr=dict(spec["qr"], kind="datamatrix"))
        self.assertTrue(any("marker kind" in e for e in W.validate(bad)[0]))

    def test_stored_grids_are_opencvs(self):
        if not T.available():
            self.skipTest("OpenCV without the aruco module")
        stored = json.load(open(os.path.join(
            ROOT, "src", "aerothon_sim", "sim_gazebo", "materials", "tag36h11_matrices.json")))
        for tag_id, cells in stored.items():
            self.assertEqual(cells, T.marker_cells(T.DEFAULT_DICTIONARY, int(tag_id)), tag_id)

    @unittest.skipUnless(T.available(), "OpenCV without the aruco module")
    def test_a_printed_board_reads_from_above(self):
        """qr_visuals' boxes, drawn as a camera above the board sees them
        (x right, y up): the printed tag is not mirrored and reads its ID."""
        import materialize_world as M
        assets = os.path.join(ROOT, "src", "aerothon_sim", "sim_gazebo", "materials")
        for tag_id in (100, 300, 500):
            sdf = M.qr_visuals(M.tag_cells(__import__("pathlib").Path(assets), tag_id),
                               1.0, "t", 0, 0.1)
            px = 400                                    # pixels per metre
            img = np.full((px * 2, px * 2), 110, np.uint8)
            for pose, size in re.findall(r"<pose>([^<]+)</pose><geometry><box><size>([^<]+)</size>", sdf):
                x, y, z = map(float, pose.split()[:3])
                sx, sy, _ = map(float, size.split())
                c0 = int(round((x - sx / 2) * px + px)), int(round(px - (y + sy / 2) * px))
                c1 = int(round((x + sx / 2) * px + px)), int(round(px - (y - sy / 2) * px))
                cv2.rectangle(img, c0, c1, 235 if z < 0.02 else 20, -1)
            found, _ = T.TagDecoder().read(img)
            self.assertEqual([p for p, _ in found], [str(tag_id)])


if __name__ == "__main__":
    unittest.main()
