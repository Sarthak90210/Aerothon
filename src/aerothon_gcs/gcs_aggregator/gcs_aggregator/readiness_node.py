#!/usr/bin/env python3
"""Readiness node — the hard interlock source (Q68).

Aggregates FC connection + GPS fix + a heartbeat on key sensor topics into a
single /mission_ready Bool the GCS uses to enable/disable arm/start, and the
mission guard can also read. Minimal but real; extend with /diagnostics_agg.
"""
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from mavros_msgs.msg import State
from sensor_msgs.msg import NavSatFix, LaserScan, Image
from std_msgs.msg import Bool


class Readiness(Node):
    def __init__(self):
        super().__init__("gcs_readiness")
        self.declare_parameter("require_gps", True)
        self.declare_parameter("sensor_timeout", 2.0)
        self.declare_parameter("image_topic", "/image_raw")
        self.connected = False
        self.gps_ok = False
        self.last = {"scan": 0.0, "image": 0.0}

        self.create_subscription(State, "/mavros/state", self._on_state, 10)
        self.create_subscription(NavSatFix, "/mavros/global_position/global",
                                 self._on_gps, qos_profile_sensor_data)
        self.create_subscription(LaserScan, "/scan",
                                 lambda m: self._touch("scan"), 5)
        self.create_subscription(Image, self.get_parameter("image_topic").value,
                                 lambda m: self._touch("image"), 5)
        self.pub = self.create_publisher(Bool, "/mission_ready", 10)
        self.create_timer(0.5, self._tick)
        self.get_logger().info("gcs_readiness up")

    def _on_state(self, m):
        self.connected = m.connected

    def _on_gps(self, m):
        # status >= 0 means a fix (NavSatStatus.STATUS_FIX == 0)
        self.gps_ok = m.status.status >= 0

    def _touch(self, key):
        self.last[key] = time.time()

    def _tick(self):
        now = time.time()
        timeout = float(self.get_parameter("sensor_timeout").value)
        scan_ok = (now - self.last["scan"]) < timeout
        image_ok = (now - self.last["image"]) < timeout
        gps_req = bool(self.get_parameter("require_gps").value)
        ready = self.connected and scan_ok and image_ok and (self.gps_ok or not gps_req)
        self.pub.publish(Bool(data=ready))


def main():
    rclpy.init()
    node = Readiness()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
