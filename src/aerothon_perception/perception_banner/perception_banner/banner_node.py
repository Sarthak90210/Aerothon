#!/usr/bin/env python3
"""Green "AeroTHON 2026" banner detection (HSV) + corridor alignment error.

Detects the green banner at the corridor mouth, gates by blob size/aspect to
reject stray greens (grass, shirts), and reports the horizontal alignment
error the mission uses to yaw/centre onto the corridor.

Best practice (see docs): only *act* on this when near the corridor-entrance
GPS waypoint — the mission tree gates by proximity; this node just reports.

Topics
  sub  <image_topic>          sensor_msgs/Image     (default /image_raw)
  pub  /percep/banner         geometry_msgs/Vector3 x: h-error[-1,1] y: v-error[-1,1] z: detected(1/0)
  pub  /percep/banner/annotated sensor_msgs/Image    for web_video_server -> GCS

Params (all runtime-tunable via `ros2 param set` for on-site calibration)
  image_topic (str)
  h_lo,h_hi,s_lo,s_hi,v_lo,v_hi (int)   HSV green range
  min_area_frac (float)                 min blob area as fraction of frame
  min_aspect,max_aspect (float)         banner width/height gate
"""

import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import Vector3


class BannerNode(Node):
    def __init__(self):
        super().__init__('perception_banner')
        p = self.declare_parameter
        p('image_topic', '/image_raw')
        # OpenCV HSV: H in [0,179]. Green ~ 40-85.
        p('h_lo', 40); p('h_hi', 85)
        p('s_lo', 70); p('s_hi', 255)
        p('v_lo', 60); p('v_hi', 255)
        p('min_area_frac', 0.01)
        p('min_aspect', 1.2); p('max_aspect', 8.0)

        self.bridge = CvBridge()
        image_topic = self.get_parameter('image_topic').value
        self.create_subscription(Image, image_topic, self.on_image, 5)
        self.pub = self.create_publisher(Vector3, '/percep/banner', 10)
        self.pub_annot = self.create_publisher(Image, '/percep/banner/annotated', 5)
        self.get_logger().info(f"perception_banner up; image_topic={image_topic}")

    def _g(self, name):
        return self.get_parameter(name).value

    def on_image(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f"cv_bridge: {e}")
            return

        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lo = np.array([self._g('h_lo'), self._g('s_lo'), self._g('v_lo')])
        hi = np.array([self._g('h_hi'), self._g('s_hi'), self._g('v_hi')])
        mask = cv2.inRange(hsv, lo, hi)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

        out = Vector3(x=0.0, y=0.0, z=0.0)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(c)
            x, y, bw, bh = cv2.boundingRect(c)
            aspect = bw / max(1, bh)
            area_ok = area >= self._g('min_area_frac') * w * h
            aspect_ok = self._g('min_aspect') <= aspect <= self._g('max_aspect')
            if area_ok and aspect_ok:
                cx, cy = x + bw / 2, y + bh / 2
                out.x = float((cx - w / 2) / (w / 2))
                out.y = float((cy - h / 2) / (h / 2))
                out.z = 1.0
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cv2.putText(frame, "BANNER", (x, max(0, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        self.pub.publish(out)
        try:
            self.pub_annot.publish(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
        except Exception:  # noqa: BLE001
            pass


def main():
    rclpy.init()
    node = BannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
