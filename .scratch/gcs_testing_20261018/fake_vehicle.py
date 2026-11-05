#!/usr/bin/env python3
"""Fake vehicle for local GCS testing: FCU topics, lidar, a growing SLAM map
and a minimal execution service. No flight code, no simulator.

The map imitates slam_toolbox: it grows as the aircraft explores a walled
arena, has speckle noise, and is republished every MAP_PERIOD seconds.
Environment: ARENA_W/ARENA_H (m), MAP_PERIOD (s), MAP_RES (m/cell).
REAL_SLAM=1: publish odom->base_link TF and leave /map and /pose to a real
slam_toolbox. WINCH_OK=1: measured winch feedback, so the mechanism task runs.
Camera images (5 Hz) go to /image_raw and the four /percep/* overlays.
"""
import json
import math
import os
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, QoSDurabilityPolicy
from mavros_msgs.msg import State, ExtendedState
from sensor_msgs.msg import BatteryState, NavSatFix, LaserScan
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, TwistStamped
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String, Bool, UInt32
from sensor_msgs.msg import Image
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
import cv2

ARENA_W = float(os.environ.get('ARENA_W', '40'))
ARENA_H = float(os.environ.get('ARENA_H', '30'))
RES = float(os.environ.get('MAP_RES', '0.05'))
MAP_PERIOD = float(os.environ.get('MAP_PERIOD', '1.0'))
LAT0, LON0 = 12.96915, 79.15583   # VIT Vellore
REAL_SLAM = os.environ.get('REAL_SLAM') == '1'
WINCH_OK = os.environ.get('WINCH_OK') == '1'
CAMERA_TOPICS = ['/image_raw', '/percep/overlay', '/percep/qr/annotated',
                 '/percep/banner/annotated', '/percep/redzone/annotated']


def lim(r):
    """Beyond the C1's 12 m range the driver reports no return (inf)."""
    return r if r < 11.9 else math.inf


class FakeVehicle(Node):
    def __init__(self):
        super().__init__('fake_vehicle')
        s = qos_profile_sensor_data
        self.p_state = self.create_publisher(State, '/mavros/state', s)
        self.p_ext = self.create_publisher(ExtendedState, '/mavros/extended_state', s)
        self.p_batt = self.create_publisher(BatteryState, '/mavros/battery', s)
        self.p_pose = self.create_publisher(PoseStamped, '/mavros/local_position/pose', s)
        self.p_slam_pose = self.create_publisher(PoseWithCovarianceStamped, '/pose', 10)
        self.p_vel = self.create_publisher(TwistStamped, '/mavros/local_position/velocity_local', s)
        self.p_gps = self.create_publisher(NavSatFix, '/mavros/global_position/global', s)
        self.p_sats = self.create_publisher(UInt32, '/mavros/global_position/raw/satellites', s)
        self.p_scan = self.create_publisher(LaserScan, '/scan', s)
        self.p_raw = self.create_publisher(LaserScan, '/scan_raw', s)
        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.p_map = self.create_publisher(OccupancyGrid, '/map', latched)
        self.p_slam = self.create_publisher(String, '/slam/status', 10)
        self.p_health = self.create_publisher(String, '/runtime/health', 10)
        self.p_devices = self.create_publisher(String, '/devices/status', 10)
        self.p_status = self.create_publisher(String, '/runtime/status', 10)
        self.p_receipt = self.create_publisher(String, '/runtime/receipt', 10)
        self.p_ready = self.create_publisher(String, '/mission_ready/detail', 10)
        self.p_ready_b = self.create_publisher(Bool, '/mission_ready', 10)
        self.p_mstate = self.create_publisher(String, '/mission/state', 10)
        self.create_subscription(String, '/runtime/request', self.on_request, 10)
        self.t0 = time.monotonic()
        self.run = None
        # Known world: walls of the arena plus a few pillars, in cells.
        self.explored = None
        self.timer_fast = self.create_timer(0.1, self.fast)
        self.timer_slow = self.create_timer(0.5, self.slow)
        if not REAL_SLAM:
            self.timer_map = self.create_timer(MAP_PERIOD, self.publish_map)
        self.tf = TransformBroadcaster(self)
        static = StaticTransformBroadcaster(self)
        st = TransformStamped()
        st.header.stamp = self.get_clock().now().to_msg()
        st.header.frame_id, st.child_frame_id = 'base_link', 'scan_mount'
        st.transform.rotation.w = 1.0
        static.sendTransform(st)
        self.p_winch = self.create_publisher(String, '/winch/status', 10)
        self.p_images = {t: self.create_publisher(Image, t, 5) for t in CAMERA_TOPICS}  # reliable, like usb_cam and the perception overlays
        self.create_timer(0.2, self.camera)
        self.frame = 0
        self.rng = np.random.default_rng(1)

    def camera(self):
        self.frame += 1
        stamp = self.get_clock().now().to_msg()
        for i, topic in enumerate(CAMERA_TOPICS):
            img = np.zeros((360, 640, 3), np.uint8)
            img[:] = (40 + 30 * i, 60, 90)
            x = int(320 + 250 * math.sin(self.frame / 10))
            cv2.circle(img, (x, 200), 40, (240, 200, 60), -1)
            cv2.putText(img, f'{topic}  #{self.frame}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
            m = Image(height=360, width=640, encoding='rgb8', step=640 * 3, data=img.tobytes())
            m.header.stamp = stamp
            m.header.frame_id = 'camera'
            self.p_images[topic].publish(m)

    def pose(self):
        t = time.monotonic() - self.t0
        # A slow lawnmower-ish loop over the arena.
        x = ARENA_W / 2 + (ARENA_W / 2 - 3) * math.sin(t / 25)
        y = ARENA_H / 2 + (ARENA_H / 2 - 3) * math.sin(t / 11)
        yaw = (t / 8) % (2 * math.pi)
        return x, y, yaw

    def ray(self, x, y, a):
        """Distance to the nearest arena wall or pillar along bearing a."""
        best = 12.0
        c, s = math.cos(a), math.sin(a)
        for d, lim in ((c, ARENA_W - x if c > 0 else x), (s, ARENA_H - y if s > 0 else y)):
            if abs(d) > 1e-6:
                best = min(best, lim / abs(d))
        for px, py in ((10, 10), (25, 18), (32, 8)):
            dx, dy = px - x, py - y
            proj = dx * c + dy * s
            if proj > 0:
                perp = abs(dx * s - dy * c)
                if perp < 0.6:
                    best = min(best, proj - math.sqrt(0.36 - perp ** 2))
        return best

    def fast(self):
        now = self.get_clock().now().to_msg()
        x, y, yaw = self.pose()
        st = State(connected=True, armed=False, guided=True, mode='GUIDED')
        st.header.stamp = now
        self.p_state.publish(st)
        ext = ExtendedState(landed_state=ExtendedState.LANDED_STATE_ON_GROUND)
        self.p_ext.publish(ext)
        ps = PoseStamped()
        ps.header.stamp = now
        ps.header.frame_id = 'map'
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = x, y, 1.5
        ps.pose.orientation.z, ps.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        self.p_pose.publish(ps)
        if REAL_SLAM:
            tf = TransformStamped()
            tf.header.stamp = now
            tf.header.frame_id, tf.child_frame_id = 'odom', 'base_link'
            tf.transform.translation.x, tf.transform.translation.y = x, y
            tf.transform.rotation.z, tf.transform.rotation.w = math.sin(yaw / 2), math.cos(yaw / 2)
            self.tf.sendTransform(tf)
        else:
            sp = PoseWithCovarianceStamped()
            sp.header = ps.header
            sp.pose.pose = ps.pose
            self.p_slam_pose.publish(sp)
        tw = TwistStamped()
        tw.twist.linear.x = 0.6
        self.p_vel.publish(tw)
        n = 720
        for pub, frame in ((self.p_scan, 'scan_mount'), (self.p_raw, 'laser')):
            sc = LaserScan()
            sc.header.stamp = now
            sc.header.frame_id = frame
            sc.angle_min, sc.angle_increment = -math.pi, 2 * math.pi / n
            sc.angle_max = sc.angle_min + sc.angle_increment * (n - 1)
            sc.range_min, sc.range_max = 0.05, 12.0
            sc.ranges = [float(lim(self.ray(x, y, yaw + sc.angle_min + i * sc.angle_increment)
                                   + self.rng.normal(0, 0.01))) for i in range(n)]
            pub.publish(sc)

    def slow(self):
        x, y, yaw = self.pose()
        g = NavSatFix()
        g.latitude = LAT0 + y / 111111
        g.longitude = LON0 + x / (111111 * math.cos(math.radians(LAT0)))
        g.status.status = 0
        self.p_gps.publish(g)
        self.p_sats.publish(UInt32(data=14))
        b = BatteryState(percentage=0.82, voltage=16.4)
        self.p_batt.publish(b)
        self.p_health.publish(String(data=json.dumps({'controller_pid': os.getpid(), 'state': 'ready'})))
        devices = {k: {'ok': True, 'reason': 'fake'} for k in ('identity', 'camera', 'lidar', 'clock')}
        devices['camera_actuator'] = {'ok': False, 'reason': 'hardware camera motion feedback has not been qualified'}
        devices['winch_actuator'] = {'ok': True, 'reason': 'fake encoder'} if WINCH_OK else {'ok': False, 'reason': 'no measured winch feedback'}
        if WINCH_OK:
            self.p_winch.publish(String(data=json.dumps({'state': 'idle', 'payout_basis': 'encoder (fake)', 'measured_payout_m': 0.0})))
        if self.run and self.run['task'] == 'mechanism' and self.run['state'] == 'Running' and time.monotonic() - self.run_started > 3:
            release = self.run['params'].get('action') == 'release'
            self.run.update(state='Outcome unknown' if release else 'Completed',
                            reason='Release requested; physical release has no confirming feedback' if release else '')
        self.p_devices.publish(String(data=json.dumps(devices)))
        self.p_slam.publish(String(data=json.dumps({'state': 'tracking', 'reason': '', 'source': 'LiDAR odometry'})))
        items = [{'key': 'gps', 'label': 'GPS', 'ok': True, 'value': 14, 'reason': 'fake'},
                 {'key': 'mode', 'label': 'Flight mode', 'ok': True, 'value': 'GUIDED', 'reason': 'fake'}]
        self.p_ready.publish(String(data=json.dumps({'ready': True, 'items': items, 'reasons': []})))
        self.p_ready_b.publish(Bool(data=True))
        self.p_mstate.publish(String(data=self.run['state'].upper() if self.run and self.run['state'] == 'Running' and self.run['task'] not in {'qr', 'slam'} else 'IDLE'))
        if self.run:
            self.p_status.publish(String(data=json.dumps(self.run)))

    def publish_map(self):
        x, y, _ = self.pose()
        # Explored region grows from the start corner; the grid grows with it.
        t = time.monotonic() - self.t0
        reach = min(1.0, 0.15 + t / 120)
        w_m, h_m = ARENA_W * reach + 4, ARENA_H * reach + 4
        w, h = int(w_m / RES), int(h_m / RES)
        ys, xs = np.mgrid[0:h, 0:w]
        wx, wy = xs * RES - 2, ys * RES - 2
        grid = np.full((h, w), -1, dtype=np.int8)
        inside = (wx >= 0) & (wx <= ARENA_W) & (wy >= 0) & (wy <= ARENA_H)
        seen = inside & (np.hypot(wx - x, wy - y) < 12 + t / 4)
        grid[seen] = 0
        wall = inside & ((wx < 0.15) | (wx > ARENA_W - 0.15) | (wy < 0.15) | (wy > ARENA_H - 0.15))
        for px, py in ((10, 10), (25, 18), (32, 8)):
            wall |= np.hypot(wx - px, wy - py) < 0.6
        grid[wall & seen] = 100
        speckle = seen & (self.rng.random((h, w)) < 0.01)
        grid[speckle] = 100
        m = OccupancyGrid()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'map'
        m.info.resolution = RES
        m.info.width, m.info.height = w, h
        m.info.origin.position.x, m.info.origin.position.y = -2.0, -2.0
        m.info.origin.orientation.w = 1.0
        m.data = grid.ravel().tolist()
        self.p_map.publish(m)

    def on_request(self, msg):
        d = json.loads(msg.data)
        cid = d['command_id']
        if d['cmd'] == 'stop':
            if self.run and self.run['state'] not in {'Completed', 'Failed', 'Outcome unknown'}:
                self.run.update(state='Completed', reason='stopped by operator')
                self.p_status.publish(String(data=json.dumps(self.run)))
            self.p_receipt.publish(String(data=json.dumps({'command_id': cid, 'state': 'Completed', 'reason': 'stopped'})))
            return
        args = d.get('args') or {}
        task = args.get('task', 'mission')
        if task == 'mechanism' and not WINCH_OK or task in {'mission', 'delivery_here', 'delivery_gps', 'banner'}:
            self.p_receipt.publish(String(data=json.dumps({'command_id': cid, 'state': 'Failed',
                'reason': 'required devices or measured actuator feedback are unavailable: camera_actuator (fake)'})))
            return
        self.run = dict(command_id=cid, task=task, params=args.get('params', {}), state='Running',
                        reason='', control_owner='Runtime', stage='observing')
        self.run_started = time.monotonic()
        self.p_status.publish(String(data=json.dumps(self.run)))


def main():
    rclpy.init()
    node = FakeVehicle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
