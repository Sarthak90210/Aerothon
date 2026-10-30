#!/usr/bin/env python3
"""The organisers' GCS inputs for a world, as the operator types them.

Before the competition the organisers hand over the judges' geofence as
latitude/longitude points and each banner's shade as #RRGGBB. In a manual
simulation run nobody publishes them for the operator: the world editor shows
these values and the operator enters them in the GCS, as on the day.

The coordinates are georeferenced on the FCU's own home position, exactly as
publish_delivery_zone.py does for scripted runs, so what the operator types
lands where the simulated arena is:

    python3 scripts/organiser_inputs.py sim/worlds/my_world.json   # waits for home
    python3 scripts/organiser_inputs.py WORLD.json --home 12.97,79.16
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src", "aerothon_mission", "mission_bt"))

import world_spec as W                                   # noqa: E402
from publish_banner_colours import DEFAULTS as SIM_COLOURS   # noqa: E402
from publish_delivery_zone import home_is_usable         # noqa: E402
from mission_bt.geofence import local_to_global          # noqa: E402


def lines(points):
    """One "latitude, longitude" per line, the GCS geofence box's format."""
    return "\n".join(f"{lat:.8f}, {lon:.8f}" for lat, lon in points)


def organiser_inputs(spec, home_lat, home_lon):
    """What the operator enters for ``spec``, about the FCU home.

    The FCU home is the spawn point, so world positions are shifted to it
    before georeferencing (the mission's local frame starts there too).
    """
    spec = W.normalise(spec)
    hx, hy = W.spawn_point(spec)

    def geo(points):
        return [local_to_global(x - hx, y - hy, home_lat, home_lon) for x, y in points]

    supplied = {k: v.upper() for k, v in (spec["banner"].get("colours") or {}).items() if v}
    colours = dict(SIM_COLOURS)
    if "exit" in supplied:
        # The field PDF's arena: blue exit boards and no orange no-entry
        # boards, so the simulator's printed orange is not on the field.
        colours.pop("orange", None)
    colours.update(supplied)
    g = spec["geofence"]
    behind = [tuple(map(float, p)) for p in g.get("behind") or []] if g.get("mode") == "behind" else []
    return {
        "home": [home_lat, home_lon],
        # The fence box: the points behind take-off when the organisers give
        # those and the zone's corners (30 Oct 2026), else the whole fence.
        "geofence": lines(geo(behind or W.fence_polygon(spec))),
        # What Apply geofence sends: their outline with the corners.
        "geofence_outline": lines(geo(W.fence_polygon(spec))),
        "delivery_zone": lines(geo(W.zone_polygon(spec))),
        "banner_colours": colours,
        # Every GCS organiser slot, "lat, lon": the six fence points (the two
        # behind take-off with a "behind" fence) and the optional course points.
        "points": points(spec, behind, geo),
    }


def points(spec, behind, geo):
    def one(p):
        (lat, lon), = geo([p])
        return f"{lat:.8f}, {lon:.8f}"
    out = {}
    if len(behind) == 2:
        out["fence_back_left"], out["fence_back_right"] = (one(p) for p in behind)
    for i, p in enumerate(W.zone_polygon(spec), 1):
        out[f"zone_{i}"] = one(p)
    c = W.course_points(spec)
    out["home"] = one(c["home"])
    out["entry_home"], out["entry_zone"] = (one(p) for p in c["entry"])
    out["exit_zone"], out["exit_home"] = (one(p) for p in c["exit"])
    return out


def wait_for_home(timeout):
    import rclpy
    from rclpy.qos import DurabilityPolicy, QoSProfile
    from mavros_msgs.msg import HomePosition

    rclpy.init()
    node = rclpy.create_node("aerothon_organiser_inputs")
    found = []

    def on_home(msg):
        if home_is_usable(msg.geo.latitude, msg.geo.longitude):
            found.append((float(msg.geo.latitude), float(msg.geo.longitude)))

    node.create_subscription(HomePosition, "/mavros/home_position/home", on_home,
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    end = node.get_clock().now().nanoseconds + int(timeout * 1e9)
    while not found and node.get_clock().now().nanoseconds < end:
        rclpy.spin_once(node, timeout_sec=0.2)
    node.destroy_node()
    rclpy.try_shutdown()
    return found[0] if found else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("world", nargs="?", help="world spec JSON")
    ap.add_argument("--home-only", action="store_true",
                    help="print only the FCU home (no world needed)")
    ap.add_argument("--home", help="lat,lon instead of waiting for the FCU home")
    ap.add_argument("--timeout", type=float, default=20.0)
    a = ap.parse_args(argv)
    if not (a.world or a.home_only):
        ap.error("a world is needed unless --home-only")
    if a.home:
        home = tuple(float(v) for v in a.home.split(","))
    else:
        home = wait_for_home(a.timeout)
        if home is None:
            print(json.dumps({"error": "no FCU home position yet; is the simulator up?"}))
            return 1
    if a.home_only:
        print(json.dumps({"home": list(home)}))
        return 0
    print(json.dumps(organiser_inputs(W.load(a.world), *home)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
