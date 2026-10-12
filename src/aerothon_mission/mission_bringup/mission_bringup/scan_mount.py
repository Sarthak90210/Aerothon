#!/usr/bin/env python3
"""Put the LD06's scan into the airframe's frame: beam 0 on the nose, CCW.

Every scan consumer -- the corridor navigator, the square-up, the gate check,
the keep-out -- reads a beam's bearing as angle_min + i * angle_increment,
relative to the nose, counter-clockwise, and wraps it. So a lidar mounted
turned, or a driver scanning clockwise, is corrected here by rewriting those
two numbers; the ranges pass through untouched. The sim publishes /scan in
the body frame already and does not run this.

    lidar_yaw_deg   where the lidar's own 0 deg points, CCW from the nose
    mirrored        the driver's angles run clockwise

Both are MEASURED on the aircraft -- from the GCS's LIDAR calibration mode, or
with scripts/check_sensors.py -- not read off a drawing.

The GCS sends a measured mount on /mission/lidar_mount; it applies at once,
with no relaunch, and is saved to `mount_file` so it survives a restart. A
saved mount wins over the launch arguments, which are only the starting
point before anything was measured. What is in force is published, latched,
on /mission/lidar_mount/applied.
"""

import json
import math
import os

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, qos_profile_sensor_data)
from std_msgs.msg import String
from sensor_msgs.msg import LaserScan

DEFAULT_MOUNT_FILE = os.path.expanduser("~/.aerothon/lidar_mount.json")


def parse_mount(data):
    """(yaw_deg, mirrored) from a mount message or file, or ValueError."""
    if not isinstance(data, dict):
        raise ValueError("a lidar mount is an object")
    yaw = float(data["yaw_deg"])
    if not math.isfinite(yaw) or not -180.0 <= yaw <= 180.0:
        raise ValueError(f"lidar yaw {yaw} is outside -180..180 deg")
    mirrored = data.get("mirrored")
    if not isinstance(mirrored, bool):
        raise ValueError("mirrored must be true or false")
    return yaw, mirrored


def mount(scan, yaw_rad, mirrored):
    """`scan` re-expressed with beam bearings in the body frame."""
    if mirrored:
        scan.angle_min, scan.angle_max = -scan.angle_min, -scan.angle_max
        scan.angle_increment = -scan.angle_increment
    scan.angle_min += yaw_rad
    scan.angle_max += yaw_rad
    return scan


class ScanMount(Node):
    def __init__(self, **kwargs):
        super().__init__("scan_mount", **kwargs)
        self.yaw = math.radians(self.declare_parameter("lidar_yaw_deg", 0.0).value)
        self.mirrored = bool(self.declare_parameter("mirrored", False).value)
        self.mount_file = self.declare_parameter(
            "mount_file", DEFAULT_MOUNT_FILE).value
        self.source = "launch arguments"
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub_applied = self.create_publisher(
            String, "/mission/lidar_mount/applied", latched)
        self._load_saved()
        self.pub = self.create_publisher(LaserScan, "/scan", qos_profile_sensor_data)
        self.create_subscription(LaserScan, "/scan_raw", self._on_scan,
                                 qos_profile_sensor_data)
        self.create_subscription(String, "/mission/lidar_mount",
                                 self._on_mount, latched)
        self._report("")

    def _load_saved(self):
        try:
            with open(self.mount_file, encoding="utf-8") as f:
                yaw, mirrored = parse_mount(json.load(f))
        except FileNotFoundError:
            return
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.get_logger().warning(f"saved lidar mount ignored: {error}")
            return
        self.yaw, self.mirrored = math.radians(yaw), mirrored
        self.source = f"saved calibration ({self.mount_file})"

    def _on_mount(self, msg):
        """A mount measured at the GCS: apply now, and keep it."""
        try:
            yaw, mirrored = parse_mount(json.loads(msg.data))
        except (ValueError, KeyError, TypeError) as error:
            self.get_logger().warning(f"lidar mount refused: {error}")
            self._report(str(error))
            return
        self.yaw, self.mirrored = math.radians(yaw), mirrored
        self.source = "GCS calibration"
        try:
            os.makedirs(os.path.dirname(self.mount_file) or ".", exist_ok=True)
            tmp = self.mount_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"yaw_deg": yaw, "mirrored": mirrored}, f)
            os.replace(tmp, self.mount_file)
        except OSError as error:
            self.get_logger().warning(f"lidar mount applied but not saved: {error}")
            self._report(f"applied, not saved: {error}")
            return
        self.get_logger().info(f"lidar mount -> yaw {yaw:+.1f} deg, "
                               f"{'mirrored' if mirrored else 'counter-clockwise'}")
        self._report("")

    def _report(self, reason):
        self.pub_applied.publish(String(data=json.dumps(dict(
            yaw_deg=round(math.degrees(self.yaw), 1), mirrored=self.mirrored,
            source=self.source, reason=reason), separators=(",", ":"))))

    def _on_scan(self, m):
        self.pub.publish(mount(m, self.yaw, self.mirrored))


def main():
    rclpy.init()
    node = ScanMount()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
