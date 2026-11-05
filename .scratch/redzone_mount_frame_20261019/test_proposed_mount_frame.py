"""PROPOSAL ONLY. Candidate regression for sim/test_redzone_georef.py.
Run: python -m pytest test_proposed_mount_frame.py --repo <root>  (or set REPO)."""
import math, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("REPO", os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, os.path.join(REPO, "src/aerothon_perception/perception_redzone"))
sys.path.insert(0, HERE)
from perception_redzone.georef import ground_point_q          # noqa: E402
from proposed_mount_frame import body_tilt_from_earth, aircraft_pitch_up  # noqa: E402

W, H, HFOV, ALT = 1280, 720, 1.0472, 10.0
NADIR = -math.pi / 2


def q_pitch_flu(p):          # +p about +y in FLU = nose DOWN
    return (math.cos(p / 2), 0.0, math.sin(p / 2), 0.0)


def q_roll(r):
    return (math.cos(r / 2), math.sin(r / 2), 0.0, 0.0)


def centre(q, cam_ctrl_rad):
    return ground_point_q(W / 2, H / 2, (W, H), HFOV, ALT, (0.0, 0.0), q, -cam_ctrl_rad)


class EarthFrameMountReading(unittest.TestCase):
    def test_pitch_sign_matches_ardupilot(self):
        self.assertAlmostEqual(aircraft_pitch_up(q_pitch_flu(math.radians(4))),
                               math.radians(-4), places=9)   # nose down = negative

    def test_level_is_unchanged(self):
        self.assertAlmostEqual(body_tilt_from_earth(NADIR, (1, 0, 0, 0)), NADIR)

    def test_nose_down_stabilised_nadir_points_straight_down(self):
        """Forward flight, 4 deg nose down: the servo holds earth nadir."""
        q = q_pitch_flu(math.radians(4))
        g = centre(q, body_tilt_from_earth(NADIR, q))
        self.assertLess(math.hypot(*g), 0.01)

    def test_current_treatment_double_counts_the_lean(self):
        """Documents the defect: earth reading used as body tilt."""
        q = q_pitch_flu(math.radians(4))
        g = centre(q, NADIR)
        self.assertAlmostEqual(math.hypot(*g), ALT * math.tan(math.radians(4)), delta=0.01)

    def test_nose_up_at_nadir_saturates_the_servo(self):
        """Body tilt cannot pass MNT1_PITCH_MIN: the lean is NOT compensated."""
        q = q_pitch_flu(math.radians(-4))
        tilt = body_tilt_from_earth(NADIR, q)
        self.assertAlmostEqual(tilt, NADIR)
        g = centre(q, tilt)
        self.assertAlmostEqual(math.hypot(*g), ALT * math.tan(math.radians(4)), delta=0.01)

    def test_roll_is_not_compensated_by_a_tilt_only_mount(self):
        q = q_roll(math.radians(5))
        g = centre(q, body_tilt_from_earth(NADIR, q))
        self.assertAlmostEqual(abs(g[1]), ALT * math.tan(math.radians(5)), delta=0.01)
        self.assertAlmostEqual(g[0], 0.0, delta=0.01)

    def test_oblique_target_is_held_in_earth_frame(self):
        q = q_pitch_flu(math.radians(6))
        ef = math.radians(-45)
        g = centre(q, body_tilt_from_earth(ef, q))
        self.assertAlmostEqual(g[0], ALT / math.tan(math.radians(45)), delta=0.01)


if __name__ == "__main__":
    unittest.main()
