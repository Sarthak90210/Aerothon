"""Camera tilt calibration: the output the servo needs for each real pose.

Two outputs, by how the camera node drives the tilt (camera_ctrl_node):

  degrees  a mount pitch command (MAV_CMD_DO_MOUNT_CONTROL, or the Gazebo
           joint), which the flight controller maps onto the servo across
           MNT1_PITCH_MIN..MAX
  us       the servo's own pulse width, set by the Pi on an FC output with
           MAV_CMD_DO_SET_SERVO (the aircraft, 27 Oct 2026: no mount, the
           servo on SERVO5)

Whether an output puts the camera at a given angle depends on the servo, its
horn and the bracket, and nothing on the aircraft measures the angle. So the
operator does: the GCS sends a pose, the operator looks at the camera, nudges
the output until the camera is really at one of the three poses below, and
records it (gcs_aggregator camera_cal).

A calibration maps each OBSERVED pose to the OUTPUT that produced it. Every
other angle the mission asks for (BANNER -20, GROUND -35, ...) is a straight
line through the neighbouring recorded points, extended past the ends.
"""

# The poses the operator can recognise by eye: level, halfway, straight down.
POSES = {"FORWARD": 0.0, "ALIGN": -45.0, "NADIR": -90.0}
# Mount pitch command: the FC clamps it to MNT1_PITCH_MIN / MNT1_PITCH_MAX.
OUTPUT_MIN_DEG, OUTPUT_MAX_DEG = -90.0, 30.0
# Two poses recorded this close together are one servo position recorded twice.
MIN_SEPARATION = {"deg": 2.0, "us": 10.0}


def clamp_output(value, lo=OUTPUT_MIN_DEG, hi=OUTPUT_MAX_DEG):
    return max(lo, min(hi, float(value)))


def validate(data, lo=OUTPUT_MIN_DEG, hi=OUTPUT_MAX_DEG, unit="deg"):
    """{pose: output} for all three poses, or ValueError with the reason.

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
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            raise ValueError(f"{pose} output must be a number ({unit})")
        if not lo <= value <= hi:
            raise ValueError(f"{pose} output {value:g} {unit} is outside the "
                             f"{lo:g}..{hi:g} {unit} range")
        points[pose] = float(value)
    unknown = set(data) - set(POSES)
    if unknown:
        raise ValueError(f"unknown pose {sorted(unknown)[0]}")
    ordered = [points[p] for p in sorted(POSES, key=POSES.get)]
    steps = [b - a for a, b in zip(ordered, ordered[1:])]
    if any(abs(s) < MIN_SEPARATION.get(unit, 0.0) for s in steps):
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


def output_for(angle_deg, points, lo=OUTPUT_MIN_DEG, hi=OUTPUT_MAX_DEG):
    """The output that puts the camera at `angle_deg`, clamped to lo..hi.
    Without points the output is the angle itself (degrees)."""
    if not points:
        return clamp_output(angle_deg, lo, hi)
    return clamp_output(_through(float(angle_deg), [POSES[p] for p in points],
                                 list(points.values())), lo, hi)


def angle_for(output, points):
    """The camera's angle at `output`, by the same calibration."""
    if not points:
        return float(output)
    return _through(float(output), list(points.values()),
                    [POSES[p] for p in points])
