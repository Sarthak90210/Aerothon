#!/usr/bin/env python3
"""HSV red-zone detection — the "smart" perception layer.

The hard backstop is the ArduPilot exclusion geofence (Q13/Q24); this node
just warns when red is visible so the GCS can flag it and the mission can be
extra-cautious.

Topics
  sub  <image_topic>        sensor_msgs/Image
  pub  /percep/redzone      std_msgs/Bool     red visible?
  pub  /percep/redzone/area std_msgs/Float32  red area fraction of frame
"""
import rclpy
from rclpy.node import Node
import cv2
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32


class RedZoneNode(Node):
    def __init__(self):
        super().__init__('perception_redzone')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('min_area_frac', 0.02)
        self.declare_parameter('s_lo', 90)
        self.declare_parameter('v_lo', 60)
        self.bridge = CvBridge()
        topic = self.get_parameter('image_topic').value
        self.create_subscription(Image, topic, self.on_image, 5)
        self.pub = self.create_publisher(Bool, '/percep/redzone', 10)
        self.pub_area = self.create_publisher(Float32, '/percep/redzone/area', 10)
        self.get_logger().info(f"perception_redzone up; image_topic={topic}")

    def on_image(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:  # noqa: BLE001
            self.get_logger().warn(f"cv_bridge: {e}"); return
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        s_lo = int(self.get_parameter('s_lo').value)
        v_lo = int(self.get_parameter('v_lo').value)
        # Red wraps the hue circle -> two bands.
        m1 = cv2.inRange(hsv, (0, s_lo, v_lo), (10, 255, 255))
        m2 = cv2.inRange(hsv, (170, s_lo, v_lo), (179, 255, 255))
        mask = cv2.bitwise_or(m1, m2)
        frac = float(np.count_nonzero(mask)) / mask.size
        visible = frac >= float(self.get_parameter('min_area_frac').value)
        self.pub.publish(Bool(data=visible))
        self.pub_area.publish(Float32(data=frac))


def main():
    rclpy.init()
    node = RedZoneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
