"""The return banner is ranged with the size of the frame it was detected in.

20 Oct 2026, laptop simulation (logs/return_lap_20261020/manual_test_winchfix):
the camera delivered 960 x 540 while the mission assumed 1280 x 720. From the
return stand-off (23.0, -6.3) the return board 6.4 m ahead was identified,
whole and centred, on ~15 consecutive frames, but ranged ~10 m. The outbound
banner lies 17 m beyond it, 12 deg off the same line of sight, and at a 10 m
range `_toward` took the return board for it and refused every frame; the
search then orbited a false lead and walked the zone edge for minutes.
"""

import math
import sys
import unittest
from pathlib import Path

import py_trees

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim"))
from test_return_gate_search import AREA_M2, HFOV, W_PX, Clock, World  # noqa: E402

FRAME_W, FRAME_H = 960, 540
FOCAL_FRAME = 0.5 * FRAME_W / math.tan(HFOV / 2)
# The detector's box is smaller than the whole board seen from above at a
# slant: live, 77,760 px against ~109,000 for the face-on board.
BOX_FRACTION = 0.714

RETURN_BOARD = (16.57, -6.55, 0.0)           # faces east, into the zone
OUTBOUND_BANNER = (6.0, -3.25)
STANDOFF = (23.0, -6.3, math.pi)


class Frame960(World):
    def __init__(self, report_frame):
        super().__init__([RETURN_BOARD], zone=(17.7, 71.6, -26.4, 15.6), start=STANDOFF)
        self.outbound_banner_xy = OUTBOUND_BANNER
        self.corridor_exit_pose = (16.3, -2.5, 3.0, 0.0)
        self.banner_image_wh = (FRAME_W, FRAME_H) if report_frame else None

    def _look(self):
        super()._look()
        if self.banner_board_area > 0:
            r2 = W_PX ** 2 / 4 / math.tan(HFOV / 2) ** 2 * AREA_M2 / self.banner_board_area
            self.banner_board_area = BOX_FRACTION * FOCAL_FRAME ** 2 * AREA_M2 / r2


def first_look(mav, n=400):
    from mission_bt.mission_tree import FindReturnBanner
    leaf = FindReturnBanner(mav, alt=5.0, clock=Clock(), hfov_rad=HFOV,
                            image_width_px=W_PX, near_range_m=9.6)
    leaf.initialise()
    mav._look()
    for _ in range(n):
        if leaf.update() != py_trees.common.Status.RUNNING or leaf.phase == "approach":
            break
    return leaf


class ReturnBannerFrameSizeTests(unittest.TestCase):

    def test_the_return_board_is_accepted_from_the_stand_off(self):
        mav = Frame960(report_frame=True)
        leaf = first_look(mav)
        self.assertEqual(leaf.phase, "approach", mav.logs[-3:])
        self.assertEqual(leaf.vi, -1, "it went searching when the board was in view")
        self.assertTrue(any("identified here" in m for m, _ in mav.logs))

    def test_even_ranged_with_the_configured_1280_focal_it_is_no_longer_refused(self):
        """The 20 Oct failure, no frame size reported: ranged ~10 m with the
        outbound banner ~23 m away on nearly the same line, the old 2x window
        refused it. Area ranging only overestimates, so `_toward` now takes a
        board ranged well short of the outbound banner as a nearer board
        (shipped_20kmh_r7 hit the same refusal with the right focal)."""
        mav = Frame960(report_frame=False)
        leaf = first_look(mav)
        self.assertEqual(leaf.phase, "approach", mav.logs[-3:])
        self.assertTrue(any("identified here" in m for m, _ in mav.logs))

    def test_range_uses_the_detection_frame(self):
        from mission_bt.mission_tree import banner_frame
        mav = Frame960(report_frame=True)
        focal, height = banner_frame(mav, HFOV, 1280, 720)
        self.assertAlmostEqual(focal, FOCAL_FRAME)
        self.assertEqual(height, FRAME_H)
        mav.banner_image_wh = None
        focal, height = banner_frame(mav, HFOV, 1280, 720)
        self.assertAlmostEqual(focal, 0.5 * 1280 / math.tan(HFOV / 2))
        self.assertEqual(height, 720)
        for bad in [(0, 540), (float("nan"), 540), ("x",), ()]:
            mav.banner_image_wh = bad
            self.assertAlmostEqual(banner_frame(mav, HFOV, 1280, 720)[0],
                                   0.5 * 1280 / math.tan(HFOV / 2))


if __name__ == "__main__":
    unittest.main()
