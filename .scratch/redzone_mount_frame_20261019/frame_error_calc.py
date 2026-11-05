#!/usr/bin/env python3
"""Offline: red-zone ground-point error when camera_ctrl reports an
EARTH-frame mount pitch but georef treats it as BODY-relative.

Truth model = ArduPilot AP_Mount_Servo (MNT1_TYPE 1, tilt only, no pan/roll
servo): body tilt demand = clamp(target_ef - ahrs_pitch, MNT1_PITCH_MIN,
MNT1_PITCH_MAX); the camera then rides the airframe at that body tilt.
Truth ray is built with explicit rotation matrices (independent of georef).
Run: python frame_error_calc.py <repo_root>
"""
import json, math, sys
import numpy as np

sys.path.insert(0, f"{sys.argv[1]}/src/aerothon_perception/perception_redzone")
from perception_redzone.georef import ground_point_q, footprint  # noqa: E402

W, H, HFOV = 1280, 720, 1.0472
PMIN, PMAX = math.radians(-90), math.radians(30)


def quat_flu(roll, pitch_flu, yaw):
    """ZYX quaternion (w,x,y,z), ENU/FLU. pitch_flu > 0 = nose DOWN."""
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch_flu / 2), math.sin(pitch_flu / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return (cr * cp * cy + sr * sp * sy, sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy)


def rot(roll, pitch_flu, yaw):
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch_flu), math.sin(pitch_flu)
    cy, sy = math.cos(yaw), math.sin(yaw)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Rz @ Ry @ Rx


def servo_body_tilt(target_ef, pitch_ap):
    """AP_Mount_Servo::update_angle_outputs + move_servo clamp (lead = 0)."""
    return min(PMAX, max(PMIN, target_ef - pitch_ap))


def truth_centre(h, roll, pitch_ap, yaw, target_ef):
    tau = servo_body_tilt(target_ef, pitch_ap)          # up positive
    ray = rot(roll, -pitch_ap, yaw) @ np.array([math.cos(tau), 0.0, math.sin(tau)])
    if ray[2] >= -1e-9:
        return None
    t = h / -ray[2]
    return (t * ray[0], t * ray[1])


def run(h, roll_deg, pitch_ap_deg, yaw_deg=30.0, target_deg=-90.0):
    roll, pap, yaw = map(math.radians, (roll_deg, pitch_ap_deg, yaw_deg))
    tgt = math.radians(target_deg)
    q = quat_flu(roll, -pap, yaw)
    truth = truth_centre(h, roll, pap, yaw, tgt)
    # current code, timed / Copter<=4.5 mount readback: actual_rad = target_ef
    cur = ground_point_q(W / 2, H / 2, (W, H), HFOV, h, (0, 0), q, -tgt)
    # Copter>=4.6 mount readback: actual_rad = clamped body demand
    body = servo_body_tilt(tgt, pap)
    v46 = ground_point_q(W / 2, H / 2, (W, H), HFOV, h, (0, 0), q, -body)
    # proposed: redzone derives body tilt from EF reading + capture-time quat
    pitch_ap_from_q = -math.asin(max(-1, min(1, 2 * (q[0] * q[2] - q[3] * q[1]))))
    fix = ground_point_q(W / 2, H / 2, (W, H), HFOV, h, (0, 0), q,
                         -servo_body_tilt(tgt, pitch_ap_from_q))
    err = lambda g: None if g is None or truth is None else round(math.dist(g, truth), 3)
    # footprint() (yaw-only) centre vs truth
    fp = footprint((W, H), HFOV, h, (0, 0), yaw, -tgt)
    fpc = None if fp is None else (sum(p[0] for p in fp) / 4, sum(p[1] for p in fp) / 4)
    return {"alt_m": h, "roll_deg": roll_deg, "pitch_ap_deg": pitch_ap_deg,
            "target_ef_deg": target_deg,
            "servo_clamped": abs(body - (tgt - pap)) > 1e-9,
            "err_current_m": err(cur), "err_46_mount_body_m": err(v46),
            "err_proposed_m": err(fix), "err_footprint_yaw_only_m": err(fpc),
            "h_tan_pitch_m": round(h * math.tan(abs(pap)), 3),
            "settled_gate_46_mount": abs(body - tgt) <= math.radians(2.0)}


rows = []
for h in (5.0, 10.0):
    for roll in (0.0, 5.0):
        for p in (-15.0, -8.0, -4.0, -2.0, 0.0, 2.0, 4.0, 8.0):
            rows.append(run(h, roll, p))
# a non-nadir EF target (ALIGN -45) for completeness
for p in (-8.0, -4.0, 4.0):
    rows.append(run(10.0, 0.0, p, target_deg=-45.0))
print(json.dumps(rows, indent=1))
