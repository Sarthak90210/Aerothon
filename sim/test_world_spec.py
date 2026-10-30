"""User-built arenas: the spec, the world it materialises, the checks.

The editor (tools/world_editor) writes a spec; materialize_world.py places it
into mission2.sdf. These tests pin that every position, size and heading in
the spec reaches the world and the organiser inputs, and that the default
spec rebuilds the shipped arena exactly -- so a custom run and a shipped run
differ only in what the person changed.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "sim"))

import world_spec as W  # noqa: E402
import materialize_world as MW  # noqa: E402

TEMPLATE = ROOT / "src/aerothon_sim/sim_gazebo/worlds/mission2.sdf"
ASSETS = ROOT / "src/aerothon_sim/sim_gazebo/materials"


def build(spec, **overrides):
    """Run the real materialiser on a spec; return (world XML root, layout)."""
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "spec.json"
        sp.write_text(json.dumps(spec))
        out = Path(d) / "world.sdf"
        lay = Path(d) / "layout.json"
        env = dict(os.environ)
        env.pop("AEROTHON_WORLD_SPEC", None)
        env.pop("AEROTHON_RANDOM_ARENA", None)
        env.update(overrides)
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/materialize_world.py"),
             "--source", str(TEMPLATE), "--assets", str(ASSETS),
             "--output", str(out), "--layout-out", str(lay),
             "--world-spec", str(sp)],
            capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise AssertionError(r.stdout + r.stderr)
        return ET.fromstring(out.read_text()), json.loads(lay.read_text()), r.stdout


def model_pose(root, name):
    for m in root.iter("model"):
        if m.get("name") == name:
            return [float(v) for v in m.find("pose").text.split()]
    raise KeyError(name)


def custom_spec():
    """Nothing where the shipped arena has it: turned, resized, re-counted."""
    s = W.default_spec()
    s["name"] = "test_custom"
    s["takeoff"] = {"x": 5.0, "y": -20.0, "yaw_deg": 30.0}
    s["corridor"] = {"x": 12.0, "y": -14.0, "yaw_deg": 25.0}
    s["delivery_zone"] = {"x": 45.0, "y": 5.0, "w": 34.0, "h": 26.0}
    s["red_zones"] = [
        {"x": 50.0, "y": 12.0, "w": 5.0, "h": 3.0, "yaw_deg": 40.0},
        {"x": 40.0, "y": -3.0, "w": 4.0, "h": 4.0, "yaw_deg": 0.0},
        {"x": 56.0, "y": -2.0, "w": 3.0, "h": 6.0, "yaw_deg": -15.0},
        {"x": 38.0, "y": 13.0, "w": 2.5, "h": 2.5, "yaw_deg": 10.0},
    ]
    s["pads"] = {"a": {"x": 33.0, "y": 0.0}, "b": {"x": 45.0, "y": 6.0},
                 "c": {"x": 57.0, "y": 10.0}, "d": {"x": 48.0, "y": -5.0},
                 "e": {"x": 34.0, "y": 14.0, "yaw_deg": 20.0}}
    s["decoys"] = [{"x": 25.0, "y": 20.0, "yaw_deg": 90.0}]
    s["geofence"] = {"mode": "polygon", "vertices": [
        [-5.0, -32.0], [70.0, -32.0], [70.0, 26.0], [20.0, 26.0], [-5.0, 0.0]]}
    s["start_target"] = "d"
    s["qr"] = {"start_m": 1.5, "target_m": 2.5}
    return s


class DefaultSpecTests(unittest.TestCase):

    def test_the_default_spec_is_valid(self):
        errs, _ = W.validate(W.default_spec())
        self.assertEqual(errs, [])

    def test_the_default_spec_rebuilds_the_shipped_arena(self):
        root, lay, _ = build(W.default_spec())
        self.assertEqual(lay["gate"], [2.0, 2.0, 0.0])
        self.assertEqual(lay["home_world"], [-2.0, 2.0])
        shipped = MW.shipped_layout()
        self.assertEqual(lay["pads"], {k: [float(a), float(b)]
                                       for k, (a, b) in shipped["pads"].items()})
        # The lanes are rebuilt from the spec; the default rebuilds the
        # shipped geometry: outbound from its banner at (2, 2), the linked
        # return lane from (12, -2) pointing back, obstacles where they were.
        self.assertEqual(model_pose(root, "corridor_outbound")[:2], [2.0, 2.0])
        p = model_pose(root, "corridor_return")
        self.assertEqual(p[:2], [12.0, -2.0])
        self.assertAlmostEqual(abs(p[5]), math.pi, places=3)
        self.assertEqual(model_pose(root, "return_aerothon_banner")[:2], [12.0, -2.0])
        centres = sorted((round(sum(x for x, _ in o["poly"]) / 4, 2),
                          round(sum(y for _, y in o["poly"]) / 4, 2))
                         for o in lay["obstacles"])
        self.assertEqual(centres, [(3.4, -0.95), (5.8, -3.05), (8.2, -0.95),
                                   (10.6, -3.05)])
        self.assertEqual(model_pose(root, "takeoff_landing_zone")[:2], [-1.0, 0.0])
        self.assertEqual(model_pose(root, "start_qr_target_a")[:2], [-1.0, 2.0])
        reds = sorted((v[0], v[1], v[2], v[3]) for v in lay["red_zones"].values())
        self.assertEqual(reds, sorted([(38.0, 5.0, 10.0, 7.0), (29.0, 10.0, 6.0, 4.0),
                                       (40.0, -11.0, 7.0, 4.0)]))


class CustomSpecTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = custom_spec()
        errs, cls.warns = W.validate(cls.spec)
        assert errs == [], errs
        cls.root, cls.lay, cls.stdout = build(cls.spec)

    def test_the_spawn_moves_and_turns_with_the_take_off_area(self):
        inc = [i for i in self.root.iter("include")
               if i.find("name").text == "aerothon_iris"][0]
        x, y, _, _, _, yaw = (float(v) for v in inc.find("pose").text.split())
        sx, sy = W.spawn_point(self.spec)
        self.assertAlmostEqual(x, sx, places=3)
        self.assertAlmostEqual(y, sy, places=3)
        self.assertAlmostEqual(yaw, math.radians(30.0), places=3)
        self.assertEqual(self.lay["home_world"], [round(sx, 3), round(sy, 3)])

    def test_the_corridor_moves_as_one_rigid_body(self):
        yaw = math.radians(25.0)
        # Return banner is (10, -4) from the forward one in corridor frame.
        ex = 12.0 + 10 * math.cos(yaw) + 4 * math.sin(yaw)
        ey = -14.0 + 10 * math.sin(yaw) - 4 * math.cos(yaw)
        p = model_pose(self.root, "return_aerothon_banner")
        self.assertAlmostEqual(p[0], ex, places=2)
        self.assertAlmostEqual(p[1], ey, places=2)
        self.assertAlmostEqual(p[5], yaw, places=3)
        self.assertEqual(self.lay["gate"][:2], [12.0, -14.0])

    def test_every_red_zone_exists_at_its_size_and_heading(self):
        names = [m.get("name") for m in self.root.iter("model")
                 if m.get("name", "").startswith("restricted_red_zone")]
        self.assertEqual(len(names), 4)
        for n, r in enumerate(self.spec["red_zones"], 1):
            p = model_pose(self.root, f"restricted_red_zone_{n}")
            self.assertAlmostEqual(p[0], r["x"], places=3)
            self.assertAlmostEqual(p[5], math.radians(r["yaw_deg"]), places=3)
            self.assertEqual(self.lay["red_zones"][f"restricted_red_zone_{n}"][2:4],
                             [r["w"], r["h"]])

    def test_the_zone_is_resized(self):
        for m in self.root.iter("model"):
            if m.get("name") == "delivery_zone_40x30":
                size = m.find(".//visual/geometry/box/size").text.split()
        self.assertEqual([float(v) for v in size[:2]], [34.0, 26.0])
        hx, hy = self.lay["home_world"]
        self.assertEqual(self.lay["delivery_zone_rect"],
                         [round(45.0 - hx, 3), round(5.0 - hy, 3), 34.0, 26.0])

    def test_the_polygon_fence_is_published_home_local(self):
        hx, hy = self.lay["home_world"]
        self.assertEqual(len(self.lay["geofence_poly"]), 5)
        want = W.fence_polygon(self.spec)
        for (x, y), (wx, wy) in zip(self.lay["geofence_poly"], want):
            self.assertAlmostEqual(x, wx - hx, places=2)
            self.assertAlmostEqual(y, wy - hy, places=2)

    def test_the_publisher_reads_the_polygon(self):
        import publish_delivery_zone as pub
        env = {"AEROTHON_GEOFENCE": ";".join(
            f"{x:.3f},{y:.3f}" for x, y in self.lay["geofence_poly"])}
        verts = pub.geofence_from_env(env)
        self.assertEqual(len(verts), 5)
        payload = json.loads(pub.geofence_payload(verts, -35.36, 149.16))
        self.assertEqual(len(payload["vertices"]), 5)

    def test_pads_decoys_and_qr_settings_come_from_the_spec(self):
        p = model_pose(self.root, "delivery_qr_target_e")
        self.assertEqual(p[:2], [34.0, 14.0])
        self.assertAlmostEqual(p[5], math.radians(20.0), places=3)
        decoys = [m.get("name") for m in self.root.iter("model")
                  if m.get("name", "").startswith("green_decoy")]
        self.assertEqual(decoys, ["green_decoy_1"])
        self.assertIn("start pad names delivery target D", self.stdout)

    def test_the_ground_covers_the_fence(self):
        for m in self.root.iter("model"):
            if m.get("name") == "site_ground":
                sx, sy = (float(v) for v in m.find(".//visual/geometry/box/size").text.split()[:2])
                cx, cy = (float(v) for v in m.find(".//visual/pose").text.split()[:2])
        for x, y in W.fence_polygon(self.spec):
            self.assertLessEqual(abs(x - cx), sx / 2)
            self.assertLessEqual(abs(y - cy), sy / 2)

    def test_the_grader_reads_sized_headed_zones_and_the_polygon(self):
        from check_track import fence_polygon, red_polygons, rect_gap
        reds = dict(red_polygons(self.lay))
        hx, hy = self.lay["home_world"]
        # The first zone's centre is inside it; a point 1 m beyond its
        # rotated long edge is 1 m away.
        r = self.spec["red_zones"][0]
        poly = reds["restricted_red_zone_1"]
        self.assertEqual(rect_gap(poly, r["x"] - hx, r["y"] - hy), 0.0)
        yaw = math.radians(r["yaw_deg"])
        nx, ny = -math.sin(yaw), math.cos(yaw)          # long edge's normal
        px = r["x"] - hx + nx * (r["h"] / 2 + 1.0)
        py = r["y"] - hy + ny * (r["h"] / 2 + 1.0)
        self.assertAlmostEqual(rect_gap(poly, px, py), 1.0, places=3)
        self.assertEqual(len(fence_polygon(self.lay)), 5)


class SeparateCorridorTests(unittest.TestCase):
    """The return corridor placed on its own, with obstacles of the user's."""

    @classmethod
    def setUpClass(cls):
        s = W.default_spec()
        s["name"] = "split"
        s["corridor"].update({"length": 12.0, "width": 4.0, "wall_height": 4.0})
        s["return_corridor"] = {
            "linked": False, "x": 13.0, "y": -9.0, "yaw_deg": 200.0,
            "length": 9.0, "width": 3.0, "wall_height": 3.4,
            "obstacles": [{"u": 3.0, "v": 0.6, "w": 0.4, "d": 1.2, "h": 3.5},
                          {"u": 6.0, "v": -0.5, "w": 0.5, "d": 1.0, "h": 3.4,
                           "yaw_deg": 20.0}]}
        s["red_zones"] = [{"x": 40.0, "y": 8.0, "w": 5.0, "h": 4.0, "yaw_deg": 0.0}]
        cls.spec = s
        errs, _ = W.validate(s)
        assert errs == [], errs
        cls.root, cls.lay, _ = build(s)

    def test_the_return_corridor_is_where_it_was_put(self):
        p = model_pose(self.root, "corridor_return")
        self.assertEqual(p[:2], [13.0, -9.0])
        self.assertAlmostEqual(p[5], math.radians(200.0), places=3)
        self.assertEqual(model_pose(self.root, "return_aerothon_banner")[:2], [13.0, -9.0])
        self.assertEqual(self.lay["corridors"]["return"][3:], [9.0, 3.0, 3.4])
        self.assertEqual(self.lay["corridors"]["outbound"][3:], [12.0, 4.0, 4.0])

    def test_the_obstacles_are_the_users(self):
        names = []
        for m in self.root.iter("model"):
            if m.get("name") == "corridor_return":
                names = [v.get("name") for v in m.iter("visual")]
        self.assertEqual(sorted(n for n in names if n.startswith("obstacle")),
                         ["obstacle_1", "obstacle_2"])
        self.assertEqual(len(self.lay["obstacles"]), 2)
        self.assertEqual(self.lay["obstacles"][0]["h"], 3.5)

    def _track_along(self, lane, across, z=3.0):
        """A straight flight down a lane's centre (offset `across`)."""
        x0, y0, yaw, L = lane[:4]
        hx, hy = self.lay["home_world"]
        rows = []
        for i in range(0, 60):
            u = -1.0 + (L + 2.0) * i / 59
            wx = x0 + u * math.cos(yaw) - across * math.sin(yaw)
            wy = y0 + u * math.sin(yaw) + across * math.cos(yaw)
            rows.append({"t": float(i), "x": wx - hx, "y": wy - hy, "z": z,
                         "armed": True, "state": "X"})
        return rows

    def test_the_grader_follows_the_moved_return_lane(self):
        from check_track import traversal
        lane = self.lay["corridors"]["return"]
        through, _ = traversal(self._track_along(lane, 0.0), self.lay, 0, False)
        self.assertTrue(through["found"])
        self.assertEqual(through["n_bad"], 0)
        beside, _ = traversal(self._track_along(lane, 2.5), self.lay, 0, False)
        self.assertTrue(beside.get("n_bad", 1) > 0 or not beside["found"])

    def test_touching_an_obstacle_fails_the_grade(self):
        from check_track import grade
        lane = self.lay["corridors"]["return"]
        # Straight down the centre: obstacle 2 (v -0.5, 1.0 m across) is hit.
        g = grade(self._track_along(lane, 0.0), self.lay)
        self.assertLess(g["closest_obstacle_m"], 0.4)
        self.assertFalse(g["checks"]["no obstacle contact"])


class ValidationTests(unittest.TestCase):

    def test_a_blocking_obstacle_is_refused(self):
        s = W.default_spec()
        s["return_corridor"]["obstacles"].append(
            {"u": 5.0, "v": 0.0, "w": 0.3, "d": 3.2, "h": 3.0})
        self.assertRefused(s, "blocks the return corridor")

    def test_obstacles_that_close_the_lane_BETWEEN_them_are_refused(self):
        """Each leaves a 1.6 m gap on its own; 0.8 m apart along the lane on
        opposite sides, the slot between them is narrower than the airframe."""
        s = W.default_spec()
        s["return_corridor"]["obstacles"] = [
            {"u": 4.0, "v": 0.8, "w": 0.35, "d": 1.9, "h": 3.4},
            {"u": 4.8, "v": -0.8, "w": 0.35, "d": 1.9, "h": 3.4}]
        self.assertRefused(s, "no way through")

    def test_the_shipped_slalom_keeps_a_metre_either_side(self):
        room = W.lane_bottleneck(W.default_spec()["return_corridor"])
        self.assertAlmostEqual(room, 1.0, delta=0.06)

    def test_a_chicane_the_navigator_will_not_take_is_warned_about(self):
        s = W.load(ROOT / "sim/worlds/my_world_offaxis.json")
        errs, warns = W.validate(s)
        self.assertTrue([w for w in warns if "will stop in front of it" in w], warns)

    def test_an_obstacle_under_the_lidar_plane_but_in_the_way_is_refused(self):
        """Live: a 3.2 m block under a 3.23 m scan plane, flown into at 3 m.
        Under the shipped board the corridor is flown at ~2.1 m, so the
        invisible band is now ~1.8-2.3 m, and it moves with the board."""
        s = W.default_spec()
        s["return_corridor"]["obstacles"][2]["h"] = 2.0
        self.assertRefused(s, "cannot see it")
        s["banner"] = {"board_bottom_m": 3.6}
        s["return_corridor"]["obstacles"][2]["h"] = 2.8
        self.assertRefused(s, "cannot see it")

    def test_overlapping_corridors_are_refused(self):
        s = W.default_spec()
        s["return_corridor"].update({"linked": False, "x": 12.0, "y": 2.0,
                                     "yaw_deg": 180.0})
        self.assertRefused(s, "corridors overlap")

    def test_a_linked_return_corridor_follows_the_outbound_one(self):
        s = W.normalise({"corridor": {"x": 5.0, "y": 1.0, "yaw_deg": 90.0}})
        r = s["return_corridor"]
        # 10 m up the outbound lane (+y) and 4 m to its starboard (+x).
        self.assertAlmostEqual(r["x"], 9.0, places=3)
        self.assertAlmostEqual(r["y"], 11.0, places=3)
        self.assertAlmostEqual(r["yaw_deg"], -90.0, places=3)

    def assertRefused(self, spec, fragment):
        errs, _ = W.validate(spec)
        self.assertTrue(any(fragment in e for e in errs), errs)

    def test_a_pad_on_red_ground_is_refused(self):
        s = W.default_spec()
        s["pads"]["a"] = {"x": 38.0, "y": 5.0}
        self.assertRefused(s, "pad A is within 1 m of red zone 1")

    def test_home_outside_the_fence_is_refused(self):
        s = W.default_spec()
        s["geofence"] = {"mode": "polygon",
                         "vertices": [[5, -20], [60, -20], [60, 20], [5, 20]]}
        self.assertRefused(s, "take-off point (FCU home) is outside")

    def test_home_too_close_to_the_fence_is_refused(self):
        s = W.default_spec()
        s["geofence"] = {"mode": "polygon",
                         "vertices": [[-3.0, -20], [60, -20], [60, 20], [-3.0, 20]]}
        self.assertRefused(s, "within 2 m of the geofence")

    def test_a_self_crossing_fence_is_refused(self):
        s = W.default_spec()
        s["geofence"] = {"mode": "polygon",
                         "vertices": [[-10, -25], [60, 25], [60, -25], [-10, 25]]}
        self.assertRefused(s, "crosses itself")

    def test_a_corridor_on_the_take_off_pad_is_refused(self):
        s = W.default_spec()
        s["corridor"] = {"x": -3.0, "y": 3.0, "yaw_deg": 0.0}
        self.assertRefused(s, "corridor overlaps the take-off pad")

    def test_a_pad_outside_the_zone_is_refused(self):
        s = W.default_spec()
        s["pads"]["b"] = {"x": 70.0, "y": 0.0}
        self.assertRefused(s, "pad B is not entirely inside")

    def test_the_materialiser_refuses_an_invalid_spec(self):
        s = W.default_spec()
        s["pads"]["a"] = {"x": 38.0, "y": 5.0}
        with self.assertRaises(AssertionError) as cm:
            build(s)
        self.assertIn("WORLD SPEC refused", str(cm.exception))

    def test_a_partial_spec_is_filled_from_the_default(self):
        s = W.normalise({"corridor": {"yaw_deg": 10.0}})
        self.assertEqual(s["corridor"]["x"], 2.0)
        self.assertEqual(len(s["pads"]), 5)


class EditorServerTests(unittest.TestCase):
    """tools/world_editor/serve.py: save, list, load, validate."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import threading
        from http.server import ThreadingHTTPServer
        spec = importlib.util.spec_from_file_location(
            "world_editor_serve", ROOT / "tools/world_editor/serve.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.mod.WORLDS = Path(cls.tmp.name)
        cls.mod.ROOT = Path(cls.tmp.name).parent
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.mod.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def call(self, method, path, body=None):
        import urllib.request
        import urllib.error
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_save_list_load(self):
        code, j = self.call("POST", "/api/worlds/unit_world", custom_spec())
        self.assertEqual(code, 200, j)
        self.assertEqual(j["errors"], [])
        code, j = self.call("GET", "/api/worlds")
        self.assertIn("unit_world", j["worlds"])
        code, j = self.call("GET", "/api/worlds/unit_world")
        self.assertEqual(j["corridor"]["yaw_deg"], 25.0)
        self.assertEqual(j["name"], "unit_world")

    def test_validate_reports_errors(self):
        s = W.default_spec()
        s["pads"]["a"] = {"x": 38.0, "y": 5.0}
        code, j = self.call("POST", "/api/validate", s)
        self.assertTrue(any("pad A" in e for e in j["errors"]))

    def test_bad_names_are_refused(self):
        code, _ = self.call("POST", "/api/worlds/..%2Fescape", W.default_spec())
        self.assertEqual(code, 400)

    def test_an_invalid_world_is_not_flown(self):
        s = W.default_spec()
        s["pads"]["a"] = {"x": 38.0, "y": 5.0}
        self.call("POST", "/api/worlds/bad_world", s)
        code, j = self.call("POST", "/api/run/bad_world")
        self.assertEqual(code, 400)
        self.assertIn("errors", j["error"])


class UnloadedPayloadFixtureTests(unittest.TestCase):
    """An unloaded airframe must not leave the cargo touching a landing skid.

    The unloaded fixture is built without the detachable joint that carries
    the payload, so the cargo left at the spawn drops onto the pad against a
    skid and records thousands of aircraft contacts before the flight arms.
    """

    def payload_and_spawn(self, spec, **env):
        root, _, _ = build(spec, **env)
        inc = [i for i in root.iter("include")
               if i.find("name").text == "aerothon_iris"][0]
        spawn = [float(v) for v in inc.find("pose").text.split()][:2]
        return model_pose(root, "aerothon_payload"), spawn

    def test_a_loaded_fixture_still_hangs_the_cargo_under_the_airframe(self):
        for spec in (W.default_spec(), custom_spec()):
            payload, spawn = self.payload_and_spawn(spec)
            self.assertAlmostEqual(payload[0], spawn[0], places=3)
            self.assertAlmostEqual(payload[1], spawn[1], places=3)

    def test_an_unloaded_fixture_parks_the_cargo_clear_on_the_pad(self):
        for spec in (W.default_spec(), custom_spec()):
            payload, spawn = self.payload_and_spawn(
                spec, AEROTHON_PAYLOAD_FIXTURE="unloaded")
            px, py = W.parked_payload_point(spec)
            self.assertAlmostEqual(payload[0], px, places=3)
            self.assertAlmostEqual(payload[1], py, places=3)
            # Clear of the airframe, and still on the pad it rests on.
            self.assertGreater(math.dist((px, py), spawn), 1.0)
            self.assertGreater(math.dist((px, py), W.start_qr_point(spec)), 1.0)
            t = spec["takeoff"]
            yaw = math.radians(t["yaw_deg"])
            u = (px - t["x"]) * math.cos(yaw) + (py - t["y"]) * math.sin(yaw)
            v = -(px - t["x"]) * math.sin(yaw) + (py - t["y"]) * math.cos(yaw)
            half_u, half_v = (s / 2 for s in W.TAKEOFF_PAD_SIZE)
            self.assertLess(abs(u), half_u - .3)
            self.assertLess(abs(v), half_v - .3)

    def test_the_template_arena_parks_it_without_a_spec(self):
        px, py = W.parked_payload_point()
        self.assertGreater(math.dist((px, py), (-2.0, 2.0)), 1.0)


def gcs_dims(**corridor):
    """The organisers' clarified GCS preset, with corridor fields overridden."""
    A = W.arena_dimensions()
    d = json.loads(json.dumps(A.BUILTIN_PRESETS["SAE Aerothon 2026 (clarified)"]))
    d["corridor"].update(corridor)
    return d


class ArenaDimensionTests(unittest.TestCase):
    """The world editor builds the world from the GCS's own dimension fields,
    so the arena flown is the arena the operator applies in the GCS."""

    def test_the_gcs_fields_reach_the_world_and_positions_stay(self):
        s = custom_spec()
        d = gcs_dims(length_m=8.0, width_m=3.0, wall_height_m=3.2, nav_height_m=2.4,
                     spacing_m=5.0)
        d["qr"].update(target_m=1.2, start_m=0.9)
        d["red_zone"]["side_m"] = 2.0
        d["obstacle"]["reach_frac"] = 0.4
        out = W.apply_dimensions(s, d)
        for lane in (out["corridor"], out["return_corridor"]):
            self.assertEqual((lane["length"], lane["width"], lane["wall_height"]), (8.0, 3.0, 3.2))
        self.assertEqual((out["corridor"]["x"], out["corridor"]["y"], out["corridor"]["yaw_deg"]),
                         (12.0, -14.0, 25.0))
        self.assertEqual(out["qr"], {"start_m": 0.9, "target_m": 1.2,
                                     "border_m": d["qr"]["border_m"],
                                     "kind": W.normalise(s)["qr"]["kind"],
                                     "ids": W.normalise(s)["qr"]["ids"]})
        self.assertTrue(all(z["w"] == z["h"] == 2.0 for z in out["red_zones"]))
        self.assertEqual(out["banner"]["board_bottom_m"], d["banner"]["suspended_bottom_m"])
        for o in out["return_corridor"]["obstacles"]:
            self.assertAlmostEqual(o["d"], 1.2)
            self.assertAlmostEqual(abs(o["v"]) + o["d"] / 2, 1.5)   # touching a wall
        self.assertEqual(out["pads"], W.normalise(s)["pads"])
        self.assertEqual(out["dimensions"]["corridor"]["spacing_m"], 5.0)

    def test_spacing_and_side_place_the_return_lane(self):
        s = W.default_spec()               # outbound at (2, 2), yaw 0, 10 m long
        right = W.apply_dimensions(s, gcs_dims(spacing_m=6.0, return_side="right"))
        left = W.apply_dimensions(s, gcs_dims(spacing_m=6.0, return_side="left"))
        self.assertEqual(right["return_corridor"]["y"], -4.0)
        self.assertEqual(left["return_corridor"]["y"], 8.0)
        self.assertEqual(right["return_corridor"]["x"], 12.0)
        # Without a spacing the shipped pose is unchanged.
        self.assertEqual(W.linked_return_pose(W.normalise(W.default_spec())), (12.0, -2.0, -180.0))

    def test_a_dimension_built_world_is_valid_and_materialises_on_its_side(self):
        s = W.apply_dimensions(W.default_spec(), gcs_dims(return_side="left", spacing_m=5.0))
        s["red_zones"] = [{"x": 38.0, "y": 5.0, "yaw_deg": 0.0}]
        s = W.apply_dimensions(s, s["dimensions"])
        errs, _ = W.validate(s)
        self.assertEqual(errs, [])
        root, _, _ = build(s)
        self.assertEqual(model_pose(root, "corridor_return")[:2], [12.0, 7.0])

    def test_a_world_edited_away_from_its_dimensions_is_refused(self):
        s = W.apply_dimensions(W.default_spec(), gcs_dims())
        s["corridor"]["width"] = 4.0
        errs, _ = W.validate(s)
        self.assertTrue(any("outbound corridor width" in e for e in errs), errs)
        s = W.apply_dimensions(W.default_spec(), gcs_dims())
        s["return_corridor"]["linked"] = False
        errs, _ = W.validate(s)
        self.assertTrue(any("stays linked" in e for e in errs), errs)

    def test_bad_dimensions_are_refused_by_the_gcs_rules(self):
        with self.assertRaisesRegex(ValueError, "navigation height"):
            W.apply_dimensions(W.default_spec(), gcs_dims(nav_height_m=3.5))

    def test_an_emptied_return_lane_gets_the_organisers_slalom(self):
        s = W.default_spec()
        s["return_corridor"]["obstacles"] = []
        out = W.apply_dimensions(s, gcs_dims(length_m=5.0))
        self.assertEqual(len(out["return_corridor"]["obstacles"]), 2)


class OrganiserInputTests(unittest.TestCase):

    def test_the_geofence_lines_land_on_the_arena_about_the_fcu_home(self):
        sys.path.insert(0, str(ROOT / "src/aerothon_mission/mission_bt"))
        import organiser_inputs as O
        from mission_bt.geofence import global_to_local
        s = custom_spec()
        home = (12.9716, 79.1594)
        out = O.organiser_inputs(s, *home)
        hx, hy = W.spawn_point(W.normalise(s))
        got = [global_to_local(*map(float, line.split(",")), *home)
               for line in out["geofence"].splitlines()]
        want = [(x - hx, y - hy) for x, y in W.fence_polygon(W.normalise(s))]
        self.assertEqual(len(got), len(want))
        for (gx, gy), (wx, wy) in zip(got, want):
            self.assertAlmostEqual(gx, wx, delta=0.01)
            self.assertAlmostEqual(gy, wy, delta=0.01)
        self.assertEqual(len(out["delivery_zone"].splitlines()), 4)
        self.assertEqual(set(out["banner_colours"]), {"green", "orange", "red"})


class EditorGcsPresetTests(unittest.TestCase):
    """Saving a dimension-built world saves the same values as a GCS preset."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        import threading
        from http.server import ThreadingHTTPServer
        spec = importlib.util.spec_from_file_location(
            "world_editor_serve_presets", ROOT / "tools/world_editor/serve.py")
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.mod.WORLDS = Path(cls.tmp.name) / "worlds"
        cls.mod.ROOT = Path(cls.tmp.name)
        cls.mod.PRESETS = Path(cls.tmp.name) / "aerothon" / "dimension_presets.json"
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.mod.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def call(self, method, path, body=None):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_the_editor_offers_exactly_the_gcs_fields(self):
        code, j = self.call("GET", "/api/dimensions")
        self.assertEqual(code, 200)
        gcs = json.loads((ROOT / "src/aerothon_gcs/tauri_app/src/arenaSchema.json").read_text())
        key = lambda f: (f["group"], f["key"], f["label"], f["min"], f["max"])  # noqa: E731
        self.assertEqual([key(f) for f in j["fields"]], [key(f) for f in gcs["fields"]])

    def test_apply_then_save_writes_the_gcs_preset_beside_the_others(self):
        self.mod.PRESETS.parent.mkdir(parents=True, exist_ok=True)
        self.mod.PRESETS.write_text(json.dumps({"Another team preset": gcs_dims()}))
        code, j = self.call("POST", "/api/apply_dimensions",
                            {"spec": W.default_spec(), "dimensions": gcs_dims(length_m=12.0)})
        self.assertEqual(code, 200, j)
        code, saved = self.call("POST", "/api/worlds/linked_world", j["spec"])
        self.assertEqual(code, 200, saved)
        self.assertEqual(saved["preset"], "World linked_world")
        presets = json.loads(self.mod.PRESETS.read_text())
        self.assertIn("Another team preset", presets)
        self.assertEqual(presets["World linked_world"]["corridor"]["length_m"], 12.0)
        self.assertEqual(presets["World linked_world"], j["spec"]["dimensions"])

    def test_bad_dimensions_are_refused_with_the_field(self):
        code, j = self.call("POST", "/api/apply_dimensions",
                            {"spec": W.default_spec(), "dimensions": gcs_dims(width_m=50.0)})
        self.assertEqual(code, 400)
        self.assertIn("Corridor width", j["error"])

    def test_the_sim_profile_carries_the_simulators_delivery_calibration(self):
        # Without one the aircraft refuses to lower the payload (19 Oct run).
        self.mod.WEB_STATE = Path(self.tmp.name) / "web"
        self.mod.write_profile(W.apply_dimensions(W.default_spec(), gcs_dims()))
        profile = json.loads((self.mod.WEB_STATE / "profiles.json").read_text())["world_sim"]
        name = profile["delivery_calibration"]
        self.assertTrue(name)
        installed = json.loads((self.mod.WEB_STATE / "devices" / name).read_text())
        self.assertEqual(installed["source"], "fcu_motor_output_squared")
        self.assertEqual(profile["marker_m"], 1.0)

    def test_a_world_without_dimensions_is_not_launched(self):
        self.call("POST", "/api/worlds/plain_world", W.default_spec())
        code, _ = self.call("POST", "/api/sim/start/plain_world")
        self.assertIn(code, (400, 409))


class GcsRangeAndColourTests(unittest.TestCase):

    def test_a_corridor_the_gcs_accepts_is_not_refused_for_its_size(self):
        # The organisers may give a 1.8 m corridor; the GCS takes 1-10 m.
        d = gcs_dims(width_m=1.8, spacing_m=2.5)
        d["banner"]["width_m"] = 1.8
        d["obstacle"]["reach_frac"] = 0.3
        errs, _ = W.validate(W.apply_dimensions(W.default_spec(), d))
        self.assertFalse([e for e in errs if "width" in e], errs)
        self.assertEqual(W.gcs_range("corridor", "width_m"), (1.0, 10.0))

    def test_half_width_obstacles_in_a_narrow_corridor_are_still_refused(self):
        d = gcs_dims(width_m=1.8, spacing_m=2.5)
        d["banner"]["width_m"] = 1.8
        errs, _ = W.validate(W.apply_dimensions(W.default_spec(), d))
        self.assertTrue(any("blocks the return corridor" in e for e in errs), errs)

    def test_the_supplied_colours_are_printed(self):
        s = W.apply_dimensions(W.default_spec(), gcs_dims())
        s["red_zones"] = [{"x": 38.0, "y": 5.0, "yaw_deg": 0.0}]
        s = W.apply_dimensions(s, s["dimensions"])
        s["banner"]["colours"] = {"green": "#07A03D", "orange": "#123456", "red": "#B00020"}
        root, _, _ = build(s)
        names = {m.get("name") for m in root.iter("model")}
        self.assertTrue({"outbound_exit_orange_banner", "return_exit_orange_banner"} <= names)
        orange = [m for m in root.iter("model") if m.get("name") == "outbound_exit_orange_banner"][0]
        self.assertIn("0.071 0.204 0.337", ET.tostring(orange, encoding="unicode"))
        red = [m for m in root.iter("model") if m.get("name") == "restricted_red_zone_1"][0]
        red_xml = ET.tostring(red, encoding="unicode")
        self.assertIn("0.690 0.000 0.126", red_xml)
        # No wording on the organisers' zones; the GCS border is printed.
        self.assertNotIn("_text_", red_xml)
        self.assertIn("red_1_border_n", red_xml)
        self.assertFalse(s["banner"]["lettered"])


if __name__ == "__main__":
    unittest.main()
