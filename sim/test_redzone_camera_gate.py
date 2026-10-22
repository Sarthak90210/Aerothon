"""Red ground is projected through the MEASURED camera, not the requested one.

Simulation, 19 October 2026: ArduPilot's servo mount holds the camera's
pitch in the EARTH frame. Flying a search lane the airframe pitches nose-down,
the Gazebo joint (body-relative) compensates, and camera_ctrl's `settled`
(measured == requested within 2 deg) went false although the camera still
looked straight down. The red-zone node stopped projecting, the search pacer
lost its red-detector timing and held the aircraft: a stop-go sweep that ran
out of time before the target. Braking nose-up the joint saturated at -90 deg,
the belly-fixed camera really looked up to 17 deg AHEAD of nadir, and
`settled` stayed true.

For a measured joint the gate is now: a fresh reading, not slewing, and the
LINE OF SIGHT (joint rotated by the capture-time attitude) within the nadir
tolerance. Timed and flight-controller mount read-backs keep `settled`.
"""
import json
import math

import cv2
import numpy as np
import pytest
import rclpy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

from perception_redzone.redzone_node import RedZoneNode

ALT = 10.0


@pytest.fixture
def node():
    rclpy.init()
    n = RedZoneNode()
    n._supplied = {'green': '#07A03D', 'orange': '#EB5A0A', 'red': '#C4161C'}
    n._red_hex = '#C4161C'
    n._hfov = .851919
    n.messages = []
    n.pub_detail.publish = n.messages.append
    yield n
    n.destroy_node()
    rclpy.shutdown()


def camera(node, joint_deg, readback='joint', settled=False, age=0.05, rate=1.0, stale=False):
    node.on_camera_state(String(data=json.dumps({
        'requested': 'NADIR', 'requested_rad': -math.pi / 2,
        'actual_rad': math.radians(joint_deg), 'settled': settled, 'stale': stale,
        'age_s': age, 'rate_dps': rate, 'readback': readback})))


def red_square_frame(side_px=160):
    frame = np.full((480, 640, 3), 80, np.uint8)
    c = (320 - side_px // 2, 240 - side_px // 2)
    cv2.rectangle(frame, c, (c[0] + side_px, c[1] + side_px), (28, 22, 196), -1)  # #C4161C
    return frame


def expose(node, pitch_nose_down_deg, frames=3):
    """Aircraft at (0, 0, ALT) facing +x, pitched; the same red square each frame."""
    th = math.radians(pitch_nose_down_deg)
    for i in range(frames):
        pose = PoseStamped()
        stamp = node.get_clock().now().nanoseconds * 1e-9 + 0.001 * (i + 1)
        pose.header.stamp.sec, pose.header.stamp.nanosec = int(stamp), int((stamp % 1) * 1e9)
        pose.pose.position.z = ALT
        # FLU body: a positive rotation about +y tilts the nose DOWN.
        pose.pose.orientation.w, pose.pose.orientation.y = math.cos(th / 2), math.sin(th / 2)
        node.on_pose(pose)
        msg = node.bridge.cv2_to_imgmsg(red_square_frame(), encoding='bgr8')
        msg.header.stamp = pose.header.stamp
        node.on_image(msg)
    return json.loads(node.messages[-1].data)


def centre(detail):
    rects = detail['exclusions']
    assert rects, detail
    xs = [(r[0] + r[1]) / 2 for r in rects]
    ys = [(r[2] + r[3]) / 2 for r in rects]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def test_a_mount_compensating_a_nose_down_pitch_still_georeferences(node):
    # 15 deg nose-down, joint at -75 deg: the camera looks straight down.
    camera(node, -75.0, settled=False)
    d = expose(node, 15.0)
    assert d['status'] == 'RED', d['reason']
    x, y = centre(d)
    assert abs(x) < 0.5 and abs(y) < 0.5, (x, y)   # directly below the aircraft


def test_a_saturated_joint_braking_nose_up_lands_ahead_of_the_aircraft(node):
    # Braking 17 deg nose-up, joint pinned at -90: the belly faces forward, the
    # view tilts ahead, and the zone is placed where the camera really looked.
    camera(node, -90.0, settled=True)
    d = expose(node, -17.0)
    assert d['status'] == 'RED', d['reason']
    x, y = centre(d)
    assert x == pytest.approx(ALT * math.tan(math.radians(17.0)), abs=0.6)
    assert abs(y) < 0.5


def test_a_line_of_sight_beyond_the_nadir_tolerance_is_not_projected(node):
    camera(node, -90.0, settled=True)                # settled, but 25 deg nose-up
    d = expose(node, -25.0, frames=1)
    assert d['status'] == 'NOT_VISIBLE'
    assert 'line of sight 25 deg off nadir' in d['reason']


def test_a_slewing_joint_is_not_projected(node):
    camera(node, -75.0, rate=40.0)
    d = expose(node, 15.0, frames=1)
    assert d['status'] == 'NOT_VISIBLE'
    assert d['reason'] == 'camera still moving'


@pytest.mark.parametrize('kw', [dict(age=0.6), dict(stale=True), dict(age=None), dict(rate=None)])
def test_an_old_or_unmeasured_joint_reading_is_not_projected(node, kw):
    camera(node, -90.0, **kw)
    d = expose(node, 0.0, frames=1)
    assert d['status'] == 'NOT_VISIBLE'
    assert d['reason'] in ('camera reading stale', 'camera still moving')


@pytest.mark.parametrize('readback', ['timed', 'mount'])
def test_timed_and_mount_readbacks_still_need_settled(node, readback):
    # Unchanged for the real drone: its read-back frame is a separate question.
    camera(node, -90.0, readback=readback, settled=False)
    assert expose(node, 0.0, frames=1)['status'] == 'NOT_VISIBLE'
    camera(node, -90.0, readback=readback, settled=True)
    assert expose(node, 0.0, frames=3)['status'] == 'RED'
