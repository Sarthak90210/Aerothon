"""Evaluation only: save the camera frame every 2 s while the mission is at a
gate (banner alignment, the return-gate search) or over a QR (start scan,
delivery search, centring), as JPEG with the FCU pose,
the camera state and the banner detector's latest detail, until OUT_DIR/frames_stop.

    python3 banner_frames.py OUT_DIR
"""
import json
import os
import sys
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

out = sys.argv[1]
frames = os.path.join(out, "banner_frames")
os.makedirs(frames, exist_ok=True)
GATES = ("BANNER", "RETURN_GATE", "RETURN_ALIGN", "DUCK", "GATE", "QR", "TARGET", "DECODE")
rclpy.init()
node = rclpy.create_node("banner_frames")
bridge = CvBridge()
st = {"img": None, "pose": None, "cam": None, "state": "", "detail": None, "qr": None}
node.create_subscription(Image, "/image_raw", lambda m: st.__setitem__("img", m), qos_profile_sensor_data)
node.create_subscription(PoseStamped, "/mavros/local_position/pose",
                         lambda m: st.__setitem__("pose", m), qos_profile_sensor_data)
node.create_subscription(String, "/camera/pose_state", lambda m: st.__setitem__("cam", m.data), 10)
node.create_subscription(String, "/mission/state", lambda m: st.__setitem__("state", m.data), 10)
node.create_subscription(String, "/percep/banner/detail", lambda m: st.__setitem__("detail", m.data), 10)
node.create_subscription(String, "/percep/qr/detail", lambda m: st.__setitem__("qr", m.data), 10)
n, last = 0, 0.0
while rclpy.ok() and not os.path.exists(os.path.join(out, "frames_stop")):
    rclpy.spin_once(node, timeout_sec=0.1)
    state = str(st["state"]).split(":")[0]
    # QR stages every 0.5 s: at the 20 km/h search a pad crosses the view in ~2 s.
    every = 0.5 if any(g in state for g in ("QR", "TARGET", "DECODE")) else 2.0
    if st["img"] is None or time.monotonic() - last < every or not any(g in state for g in GATES):
        continue
    p = st["pose"].pose if st["pose"] else None
    name = f"{n:04d}_{state}"
    cv2.imwrite(os.path.join(frames, name + ".jpg"), bridge.imgmsg_to_cv2(st["img"], "bgr8"),
                [cv2.IMWRITE_JPEG_QUALITY, 92])
    with open(os.path.join(frames, name + ".json"), "w") as f:
        json.dump({"state": st["state"], "camera": st["cam"], "detail": st["detail"], "qr": st["qr"],
                   "pos": [p.position.x, p.position.y, p.position.z] if p else None,
                   "q": [p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w] if p else None},
                  f)
    n, last, st["img"] = n + 1, time.monotonic(), None
print("saved", n, flush=True)
