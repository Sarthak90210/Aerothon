#!/usr/bin/env python3
"""QR detection + target matching (OpenCV QRCodeDetector).

Two jobs in Mission 2:
  1. START QR  — decode the delivery target string once at ~5 m.
  2. TARGET QR — during the lawnmower sweep at 10 m, report whether the
     currently-visible QR matches that target, and where it is in frame
     (for drop alignment).

Topics
  sub  <image_topic>            sensor_msgs/Image      (default /image_raw)
  sub  /mission/target          std_msgs/String        set/override the target payload
  pub  /percep/qr/decoded       std_msgs/String        best-visible decoded payload ("" if none)
  pub  /percep/qr/matched       std_msgs/Bool          is the target QR currently visible?
  pub  /percep/qr/target_offset geometry_msgs/Vector3  x,y in [-1,1] from image centre; z=1 if matched
  pub  /percep/qr/annotated     sensor_msgs/Image      for web_video_server -> GCS

Params
  image_topic (str)     input camera topic
  target (str)          target payload to match (also settable via /mission/target)
  match_mode (str)      "exact" | "substring"
  process_every (int)   process 1 of every N frames (CPU throttle)

Note: QRCodeDetector is the simplest detector; if 10 m reads are weak, swap to
cv2.wechat_qrcode.WeChatQRCode (same opencv_contrib dep, model files only).
"""

import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Vector3


class QrNode(Node):
    def __init__(self):
        super().__init__('perception_qr')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('target', '')
        self.declare_parameter('match_mode', 'exact')
        self.declare_parameter('process_every', 1)

        image_topic = self.get_parameter('image_topic').value
        self.target = self.get_parameter('target').value
        self.match_mode = self.get_parameter('match_mode').value
        self.process_every = max(1, int(self.get_parameter('process_every').value))

        self.bridge = CvBridge()
        self.detector = cv2.QRCodeDetector()
        self._frame_i = 0

        self.create_subscription(Image, image_topic, self.on_image, 5)
        self.create_subscription(String, '/mission/target', self.on_target, 10)
        self.pub_decoded = self.create_publisher(String, '/percep/qr/decoded', 10)
        self.pub_matched = self.create_publisher(Bool, '/percep/qr/matched', 10)
        self.pub_offset = self.create_publisher(Vector3, '/percep/qr/target_offset', 10)
        self.pub_annot = self.create_publisher(Image, '/percep/qr/annotated', 5)

        self.get_logger().info(
            f"perception_qr up; image_topic={image_topic} target='{self.target}'")

    def on_target(self, msg: String):
        self.target = msg.data
        self.get_logger().info(f"target set -> '{self.target}'")

    def _matches(self, payload: str) -> bool:
        if not self.target or not payload:
            return False
        if self.match_mode == 'substring':
            return self.target in payload or payload in self.target
        return payload == self.target

    def on_image(self, msg: Image):
        self._frame_i += 1
        if self._frame_i % self.process_every:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f"cv_bridge: {e}")
            return

        h, w = frame.shape[:2]
        decoded_best = ""
        matched = False
        offset = Vector3(x=0.0, y=0.0, z=0.0)

        try:
            ok, infos, points, _ = self.detector.detectAndDecodeMulti(frame)
        except cv2.error:
            ok, infos, points = False, [], None

        if ok and points is not None:
            for info, quad in zip(infos, points):
                if not info:
                    continue
                quad = quad.astype(int)
                is_match = self._matches(info)
                color = (0, 255, 0) if is_match else (0, 180, 255)
                cv2.polylines(frame, [quad], True, color, 2)
                cv2.putText(frame, info[:24], tuple(quad[0]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                if not decoded_best:
                    decoded_best = info
                if is_match:
                    matched = True
                    decoded_best = info
                    cx, cy = quad.mean(axis=0)
                    offset.x = float((cx - w / 2) / (w / 2))   # [-1,1] right+
                    offset.y = float((cy - h / 2) / (h / 2))   # [-1,1] down+
                    offset.z = 1.0

        self.pub_decoded.publish(String(data=decoded_best))
        self.pub_matched.publish(Bool(data=matched))
        self.pub_offset.publish(offset)
        try:
            self.pub_annot.publish(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
        except Exception:  # noqa: BLE001
            pass


def main():
    rclpy.init()
    node = QrNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
