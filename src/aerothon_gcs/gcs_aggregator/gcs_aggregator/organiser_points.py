"""The organisers' points and the operator's course points, as the GCS holds them.

The venue (30 Oct 2026) gives six fence points: two behind take-off and the
delivery zone's four corners. They come first and are required. Home and the
two corridors' ends are optional; without them the mission finds everything
with its camera and lidar, as it always has. Each point is typed, or recorded
by taking the aircraft to the spot and pressing Record: its own GPS averaged
over RECORD_S, refused without a 3D fix or with fewer than MIN_SATS.

Apply sends the fence (the outline of the six), the zone (the four corners)
and the optional course points (/mission/course_points) to the aircraft.
"""

import json
import math
import os

# (key, label, required). Priority order: the six fence points first.
SLOTS = (
    ("fence_back_left", "Fence point behind take-off, left", True),
    ("fence_back_right", "Fence point behind take-off, right", True),
    ("zone_1", "Delivery-zone corner 1", True),
    ("zone_2", "Delivery-zone corner 2", True),
    ("zone_3", "Delivery-zone corner 3", True),
    ("zone_4", "Delivery-zone corner 4", True),
    ("home", "Home (take-off pad)", False),
    ("entry_home", "Entry corridor, home-side mouth", False),
    ("entry_zone", "Entry corridor, zone-side mouth", False),
    ("exit_zone", "Exit corridor, zone-side mouth", False),
    ("exit_home", "Exit corridor, home-side mouth", False),
)
KEYS = tuple(k for k, _, _ in SLOTS)
FENCE_KEYS = ("fence_back_left", "fence_back_right")
ZONE_KEYS = ("zone_1", "zone_2", "zone_3", "zone_4")
RECORD_S = 5.0
MIN_SATS = 8
MIN_SAMPLES = 5
# A recording whose fixes wander further than this from their mean is refused:
# the aircraft moved, or the fix is poor.
MAX_SPREAD_M = 2.5
EARTH_R = 6378137.0


def metres_between(a, b):
    """Ground distance between two (lat, lon) points, equirectangular."""
    lat = math.radians((a[0] + b[0]) / 2.0)
    dx = math.radians(b[1] - a[1]) * EARTH_R * math.cos(lat)
    dy = math.radians(b[0] - a[0]) * EARTH_R
    return math.hypot(dx, dy)


def valid_point(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)
            and -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if abs(lat) < 1e-7 and abs(lon) < 1e-7:
        return None                     # MAVROS's unset (0, 0)
    return lat, lon


class Recorder:
    """Average the aircraft's GPS for one slot; `poll` returns the outcome."""

    def __init__(self, slot, now, seconds=RECORD_S):
        self.slot = slot
        self.t0 = float(now)
        self.seconds = float(seconds)
        self.samples = []
        self.fault = ""

    def add(self, lat, lon, fix_ok, sats):
        if self.fault:
            return
        if not fix_ok:
            self.fault = "the GPS fix was lost while recording"
            return
        if sats is not None and sats < MIN_SATS:
            self.fault = f"{sats} satellites while recording; {MIN_SATS} needed"
            return
        p = valid_point(lat, lon)
        if p is not None:
            self.samples.append(p)

    def status(self, now):
        return {"slot": self.slot, "elapsed_s": round(float(now) - self.t0, 1),
                "samples": len(self.samples)}

    def poll(self, now):
        """None while recording, else ``(point dict, '')`` or ``(None, reason)``."""
        if self.fault:
            return None, self.fault
        if float(now) - self.t0 < self.seconds:
            return None
        if len(self.samples) < MIN_SAMPLES:
            return None, f"only {len(self.samples)} GPS fixes in {self.seconds:.0f} s"
        lat = sum(p[0] for p in self.samples) / len(self.samples)
        lon = sum(p[1] for p in self.samples) / len(self.samples)
        spread = max(metres_between((lat, lon), p) for p in self.samples)
        if spread > MAX_SPREAD_M:
            return None, (f"fixes spread {spread:.1f} m (the aircraft moved or "
                          f"the fix is poor); {MAX_SPREAD_M:.1f} m allowed")
        return {"lat": round(lat, 8), "lon": round(lon, 8), "source": "recorded",
                "samples": len(self.samples), "spread_m": round(spread, 2)}, ""


def typed(lat, lon):
    p = valid_point(lat, lon)
    if p is None:
        return None
    return {"lat": p[0], "lon": p[1], "source": "typed"}


def convex_hull(points):
    """Counter-clockwise hull of (lat, lon) points, in (lon, lat) order."""
    pts = sorted(set((p[1], p[0]) for p in points))
    if len(pts) <= 2:
        return [(y, x) for x, y in pts]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and cross(out[-2], out[-1], p) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return [(y, x) for x, y in half(pts) + half(pts[::-1])]


def missing(points):
    """Labels of the required points not yet set, in priority order."""
    return [label for key, label, required in SLOTS
            if required and key not in points]


def boundaries(points):
    """``(fence vertices, zone corners, course payload, '')`` from the stored
    points, or ``(None, None, None, reason)``. Vertices as {"lat", "lon"}."""
    gone = missing(points)
    if gone:
        return None, None, None, "not set: " + ", ".join(gone)

    def ll(key):
        return (points[key]["lat"], points[key]["lon"])
    zone = [ll(k) for k in ZONE_KEYS]
    fence = convex_hull([ll(k) for k in FENCE_KEYS] + zone)
    if len(fence) < 3:
        return None, None, None, "the fence points enclose no area"
    course = {"home": None, "entry": None, "exit": None}
    if "home" in points:
        course["home"] = dict(zip(("lat", "lon"), ll("home")))
    for name, ends in (("entry", ("entry_home", "entry_zone")),
                       ("exit", ("exit_zone", "exit_home"))):
        if all(k in points for k in ends):
            course[name] = [dict(zip(("lat", "lon"), ll(k))) for k in ends]
    return ([{"lat": a, "lon": b} for a, b in fence],
            [{"lat": a, "lon": b} for a, b in zone], course, "")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return {}
    out = {}
    for key, value in (raw.items() if isinstance(raw, dict) else ()):
        if key in KEYS and isinstance(value, dict):
            p = valid_point(value.get("lat"), value.get("lon"))
            if p is not None:
                out[key] = dict(value, lat=p[0], lon=p[1])
    return out


def save(path, points):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(points, f, indent=2, sort_keys=True)
    os.replace(tmp, path)
