"""Where the LD06 is mounted, measured from two boxes in its raw scan.

The stack reads every beam's bearing off the nose, counter-clockwise; the
lidar is wherever its bracket put it and its driver may scan either way.
Hold a box ~1 m straight ahead of the nose, then ~1 m to port: where each
shows up in the driver's raw scan (/scan_raw) gives the mount yaw and the
scan direction (`solve_mount`), which mission_bringup's scan_mount applies.

Shared by the GCS calibration mode (gcs_aggregator) and the bench script
(scripts/check_sensors.py), so the two cannot disagree. Pure arithmetic.
"""

import math

SELF_M = 0.3          # nearer than this is the airframe or the bracket
MAX_TURN_ERROR_DEG = 20.0


def nearest_bearing(scan, self_m=SELF_M):
    """(bearing_deg, range_m) of the nearest return in the scan's own frame,
    or None. Returns nearer than `self_m` are the airframe."""
    lo = max(float(self_m), float(getattr(scan, "range_min", 0.0)))
    best = None
    for i, r in enumerate(scan.ranges):
        try:
            r = float(r)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(r) or r < lo:
            continue
        if best is None or r < best[1]:
            best = (i, r)
    if best is None:
        return None
    a = scan.angle_min + best[0] * scan.angle_increment
    return math.degrees(math.atan2(math.sin(a), math.cos(a))), best[1]


def solve_mount(front_deg, port_deg):
    """(lidar_yaw_deg, mirrored, error_deg) that put `front` on the nose and
    `port` at +90: body = raw + yaw, or -raw + yaw when the driver runs
    clockwise. `error_deg` is how far the two captures are from 90 deg
    apart -- large means a box was not where it was said to be."""
    turn = (port_deg - front_deg + 180.0) % 360.0 - 180.0
    mirrored = turn < 0.0
    yaw = front_deg if mirrored else -front_deg
    return (yaw + 180.0) % 360.0 - 180.0, mirrored, abs(abs(turn) - 90.0)


def result(captures):
    """The calibration from {'ahead': (deg, m), 'port': (deg, m)}, or None
    while either is missing. Never claims a mount it cannot stand behind."""
    ahead, port = captures.get("ahead"), captures.get("port")
    if not ahead or not port:
        return None
    yaw, mirrored, err = solve_mount(ahead[0], port[0])
    ok = err <= MAX_TURN_ERROR_DEG
    return {"yaw_deg": round(yaw, 1), "mirrored": bool(mirrored),
            "error_deg": round(err, 1), "ok": ok,
            "reason": "" if ok else (
                f"the port box read {err:.0f} deg away from 90 deg off the nose; "
                "capture again with each box square to the aircraft")}
