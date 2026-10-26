"""Camera tilt calibration: the output the servo needs for each real pose.

The flight controller turns a mount pitch command into PWM linearly between
SERVO5_MIN and SERVO5_MAX across MNT1_PITCH_MIN..MNT1_PITCH_MAX
(aerothon_hardware.parm). Whether that PWM puts the camera at the commanded
angle depends on the servo, its horn and the bracket, and nothing on the
aircraft measures the angle. So the operator does: the GCS sends a pose, the
operator looks at the camera, nudges the output until the camera is really at
one of the three poses below, and records it (gcs_aggregator camera_cal).

A calibration maps each OBSERVED pose to the OUTPUT -- the mount pitch command
in degrees -- that produced it. Every other angle the mission asks for
(BANNER -20, GROUND -35, ...) is a straight line through the neighbouring
recorded points, extended past the ends. Without a calibration the output is
the angle itself, as before.
"""

import math

# The poses the operator can recognise by eye: level, halfway, straight down.
POSES = {"FORWARD": 0.0, "ALIGN": -45.0, "NADIR": -90.0}
# MNT1_PITCH_MIN / MNT1_PITCH_MAX: the FC clamps a command to this range.
OUTPUT_MIN_DEG, OUTPUT_MAX_DEG = -90.0, 30.0
# Two poses recorded this close together are one servo position recorded twice.
MIN_SEPARATION_DEG = 2.0


def clamp_output(deg):
    return max(OUTPUT_MIN_DEG, min(OUTPUT_MAX_DEG, float(deg)))


def validate(data):
    """{pose: output_deg} for all three poses, or ValueError with the reason.

    The outputs must run in one direction through the poses (either way: a
    servo mounted reversed is still a calibration), or the mapping would
    send two angles to one position."""
    if not isinstance(data, dict):
        raise ValueError("a camera calibration is an object of pose: output")
    points = {}
    for pose in POSES:
        if pose not in data:
            raise ValueError(f"no output recorded for {pose}")
        value = data[pose]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{pose} output must be a number of degrees")
        if not OUTPUT_MIN_DEG <= value <= OUTPUT_MAX_DEG:
            raise ValueError(f"{pose} output {value:g} deg is outside the mount's "
                             f"{OUTPUT_MIN_DEG:g}..{OUTPUT_MAX_DEG:g} deg")
        points[pose] = float(value)
    unknown = set(data) - set(POSES)
    if unknown:
        raise ValueError(f"unknown pose {sorted(unknown)[0]}")
    ordered = [points[p] for p in sorted(POSES, key=POSES.get)]
    steps = [b - a for a, b in zip(ordered, ordered[1:])]
    if any(abs(s) < MIN_SEPARATION_DEG for s in steps):
        raise ValueError("two poses were recorded at the same output")
    if not (all(s > 0 for s in steps) or all(s < 0 for s in steps)):
        raise ValueError("the outputs do not run in one direction from straight down "
                         "to forward; record each pose again")
    return points


def _through(x, xs, ys):
    """Straight line through the two neighbouring points, extended past the ends."""
    pairs = sorted(zip(xs, ys))
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    i = 0
    while i < len(xs) - 2 and x > xs[i + 1]:
        i += 1
    x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def output_for(angle_deg, points):
    """The output that puts the camera at `angle_deg` (clamped to the mount)."""
    if not points:
        return clamp_output(angle_deg)
    return clamp_output(_through(float(angle_deg), [POSES[p] for p in points],
                                 list(points.values())))


def angle_for(output_deg, points):
    """The camera's angle at `output_deg`, by the same calibration."""
    if not points:
        return float(output_deg)
    return _through(float(output_deg), list(points.values()),
                    [POSES[p] for p in points])
