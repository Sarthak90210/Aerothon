"""PROPOSAL ONLY (not applied to src). Candidate addition to
perception_redzone/georef.py: turn an EARTH-frame servo-mount pitch into the
BODY tilt the camera actually has, the way ArduPilot AP_Mount_Servo does.

AP_Mount_Servo::update_angle_outputs (MNT1_TYPE 1, requires_stabilization):
    body_tilt = target_ef_pitch - ahrs_pitch      (tilt servo only; no roll/pan)
then move_servo clamps to [MNT1_PITCH_MIN, MNT1_PITCH_MAX]. MNT1_PITCH_LEAD
is 0 in the recorded parameters, so the lead term is omitted.

Angles use camera_ctrl's convention: up positive, NADIR = -pi/2.
"""
import math


def aircraft_pitch_up(quat_wxyz):
    """ArduPilot-convention pitch (nose UP positive) from a MAVROS ENU/FLU
    quaternion. FLU +pitch about +y is nose DOWN, hence the sign flip."""
    w, x, y, z = quat_wxyz
    n = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    w, x, y, z = w / n, x / n, y / n, z / n
    return -math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))


def body_tilt_from_earth(pitch_ef_rad, quat_wxyz, pitch_min_rad=math.radians(-90.0),
                         pitch_max_rad=math.radians(30.0)):
    """Body-relative tilt of a stabilised tilt servo holding `pitch_ef_rad`."""
    tilt = pitch_ef_rad - aircraft_pitch_up(quat_wxyz)
    return min(pitch_max_rad, max(pitch_min_rad, tilt))
