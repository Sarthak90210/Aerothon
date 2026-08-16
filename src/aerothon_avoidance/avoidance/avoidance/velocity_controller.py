#!/usr/bin/env python3
"""Reactive corridor-centering + obstacle-braking velocity controller.

The heart of the companion-side avoidance (see docs/ARCHITECTURE.md §4-5).
Consumes the RPLidar C1 /scan and emits BODY-FRAME velocity setpoints so the
drone stays centred in the 3.5 m corridor and brakes for obstacles ahead —
while GPS position setpoints (from the mission tree) handle the big legs.

Body frame (MAV_FRAME_BODY_OFFSET_NED): x forward, y right, z down.

Control law
  vx (forward): cruise, ramped down as the front gets close; 0 inside stop_dist.
  vy (lateral): k_center * (right_dist - left_dist)  -> steer toward the roomier
                side to sit on the corridor centreline. Clamped to max_lateral.
  vz          : 0 (hold corridor altitude; baro).
  yaw_rate    : 0 (heading was set by banner-align before corridor entry).

Topics
  sub  <scan_topic>            sensor_msgs/LaserScan  (default /scan)
  sub  /avoidance/enable       std_msgs/Bool          gate output on/off (mission-controlled)
  sub  /avoidance/cruise       std_msgs/Float32       override cruise speed at runtime
  pub  /mavros/setpoint_raw/local  mavros_msgs/PositionTarget  body-frame velocity
  pub  /avoidance/status       geometry_msgs/Vector3  x=front_dist y=centering_err z=cmd_vx

Params (runtime-tunable)
  scan_topic, rate_hz, cruise_speed, front_fov_deg, side_fov_deg,
  brake_dist, stop_dist, k_center, max_lateral
"""

import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32
from geometry_msgs.msg import Vector3
from mavros_msgs.msg import PositionTarget

# PositionTarget type_mask: use vx,vy,vz + yaw_rate; ignore pos, accel, yaw.
IGN_PX, IGN_PY, IGN_PZ = 1, 2, 4
IGN_AFX, IGN_AFY, IGN_AFZ = 64, 128, 256
IGN_YAW = 1024
VEL_YAWRATE_MASK = (IGN_PX | IGN_PY | IGN_PZ |
                    IGN_AFX | IGN_AFY | IGN_AFZ | IGN_YAW)  # = 1479
FRAME_BODY_OFFSET_NED = 9


class VelocityController(Node):
    def __init__(self):
        super().__init__('velocity_controller')
        p = self.declare_parameter
        p('scan_topic', '/scan')
        p('rate_hz', 20.0)
        p('cruise_speed', 0.8)     # m/s forward in corridor
        p('front_fov_deg', 40.0)   # +/- around forward for the brake sector
        p('side_fov_deg', 30.0)    # +/- around +/-90 deg for wall sectors
        p('brake_dist', 2.5)       # start slowing (m)
        p('stop_dist', 0.8)        # full stop (m)
        p('k_center', 0.6)         # lateral gain (m/s per m of imbalance)
        p('max_lateral', 0.6)      # clamp lateral speed (m/s)

        self.enabled = False
        self.cruise = float(self.get_parameter('cruise_speed').value)
        self.scan = None

        scan_topic = self.get_parameter('scan_topic').value
        self.create_subscription(LaserScan, scan_topic, self._on_scan, 5)
        self.create_subscription(Bool, '/avoidance/enable', self._on_enable, 10)
        self.create_subscription(Float32, '/avoidance/cruise', self._on_cruise, 10)
        self.pub_sp = self.create_publisher(PositionTarget, '/mavros/setpoint_raw/local', 10)
        self.pub_status = self.create_publisher(Vector3, '/avoidance/status', 10)

        rate = float(self.get_parameter('rate_hz').value)
        self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(f"velocity_controller up; scan={scan_topic}")

    def _on_enable(self, m: Bool):
        self.enabled = m.data
        self.get_logger().info(f"avoidance {'ENABLED' if m.data else 'disabled'}")

    def _on_cruise(self, m: Float32):
        self.cruise = float(m.data)

    def _on_scan(self, m: LaserScan):
        self.scan = m

    def _g(self, n):
        return float(self.get_parameter(n).value)

    def _sector_min(self, scan: LaserScan, center_rad: float, half_fov_rad: float):
        """Min valid range within [center-half, center+half]."""
        best = scan.range_max
        found = False
        for i, r in enumerate(scan.ranges):
            if not math.isfinite(r) or r <= scan.range_min or r > scan.range_max:
                continue
            ang = scan.angle_min + i * scan.angle_increment
            # wrap angle difference into [-pi, pi]
            d = (ang - center_rad + math.pi) % (2 * math.pi) - math.pi
            if abs(d) <= half_fov_rad:
                if r < best:
                    best = r
                    found = True
        return best if found else scan.range_max

    def _tick(self):
        if not self.enabled or self.scan is None:
            return
        scan = self.scan
        front_half = math.radians(self._g('front_fov_deg'))
        side_half = math.radians(self._g('side_fov_deg'))

        front = self._sector_min(scan, 0.0, front_half)
        left = self._sector_min(scan, math.pi / 2, side_half)
        right = self._sector_min(scan, -math.pi / 2, side_half)

        brake, stop = self._g('brake_dist'), self._g('stop_dist')
        if front <= stop:
            vx = 0.0
        elif front >= brake:
            vx = self.cruise
        else:
            vx = self.cruise * (front - stop) / max(1e-3, (brake - stop))

        center_err = right - left               # +ve => closer to left wall
        vy = self._g('k_center') * center_err    # steer right (+y) toward centre
        vy = max(-self._g('max_lateral'), min(self._g('max_lateral'), vy))

        sp = PositionTarget()
        sp.header.stamp = self.get_clock().now().to_msg()
        sp.coordinate_frame = FRAME_BODY_OFFSET_NED
        sp.type_mask = VEL_YAWRATE_MASK
        sp.velocity.x = float(vx)     # forward
        sp.velocity.y = float(vy)     # right
        sp.velocity.z = 0.0           # hold altitude
        sp.yaw_rate = 0.0
        self.pub_sp.publish(sp)

        self.pub_status.publish(Vector3(x=float(front), y=float(center_err), z=float(vx)))


def main():
    rclpy.init()
    node = VelocityController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
