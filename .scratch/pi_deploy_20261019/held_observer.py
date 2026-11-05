"""Bounded subscriber-only observation. No publishers, services or parameters."""
import collections
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped, TwistStamped
from sensor_msgs.msg import LaserScan, Imu
from std_msgs.msg import String
from mavros_msgs.msg import State
from nav_msgs.msg import OccupancyGrid
from tf2_msgs.msg import TFMessage

rclpy.init()
node = Node('held_mapping_readonly_observer_20261019')
started = time.monotonic()
counts = collections.Counter()
last = {}

def stamp(m):
    return m.header.stamp.sec + m.header.stamp.nanosec / 1e9

def xyz(v):
    return [v.x, v.y, v.z]

def quat(q):
    return [q.x, q.y, q.z, q.w]

def emit(kind, data):
    counts[kind] += 1
    print(json.dumps(dict(kind=kind, received_s=time.monotonic()-started,
                         ros_now_s=node.get_clock().now().nanoseconds/1e9, **data),
                     allow_nan=False, separators=(',', ':')), flush=True)

def scan(m, kind):
    emit(kind, dict(stamp=stamp(m), frame=m.header.frame_id,
        angle_min=m.angle_min, angle_increment=m.angle_increment,
        range_min=m.range_min, range_max=m.range_max, scan_time=m.scan_time,
        time_increment=m.time_increment,
        ranges=[float(x) if math.isfinite(x) else None for x in m.ranges]))

def pose(m):
    now=time.monotonic()
    if now-last.get('pose', 0) < .095: return
    last['pose']=now
    emit('pose', dict(stamp=stamp(m), position=xyz(m.pose.position),
                      orientation=quat(m.pose.orientation)))

def imu(m):
    now=time.monotonic()
    if now-last.get('imu', 0) < .095: return
    last['imu']=now
    emit('imu', dict(stamp=stamp(m), orientation=quat(m.orientation),
        angular_velocity=xyz(m.angular_velocity), linear_acceleration=xyz(m.linear_acceleration)))

def velocity(m):
    now=time.monotonic()
    if now-last.get('velocity', 0) < .095: return
    last['velocity']=now
    emit('velocity', dict(stamp=stamp(m), linear=xyz(m.twist.linear), angular=xyz(m.twist.angular)))

def transform(m, kind):
    selected=[]
    for t in m.transforms:
        if kind=='tf_static' or t.child_frame_id.startswith('lidar_mapping'):
            selected.append(dict(stamp=stamp(t), parent=t.header.frame_id,
                child=t.child_frame_id, translation=xyz(t.transform.translation),
                rotation=quat(t.transform.rotation)))
    if selected: emit(kind, dict(transforms=selected))

def grid(m):
    data=dict(stamp=stamp(m), frame=m.header.frame_id, width=m.info.width,
        height=m.info.height, resolution=m.info.resolution,
        origin=xyz(m.info.origin.position), orientation=quat(m.info.origin.orientation))
    if not counts['map']: data['data']=list(m.data)
    emit('map', data)

node.create_subscription(LaserScan, '/scan', lambda m:scan(m,'scan'), qos_profile_sensor_data)
node.create_subscription(LaserScan, '/scan_slam', lambda m:scan(m,'scan_slam'), qos_profile_sensor_data)
node.create_subscription(String, '/slam/status', lambda m:emit('status', json.loads(m.data)), 10)
node.create_subscription(PoseStamped, '/mavros/local_position/pose', pose, qos_profile_sensor_data)
node.create_subscription(TwistStamped, '/mavros/local_position/velocity_local', velocity, qos_profile_sensor_data)
node.create_subscription(Imu, '/mavros/imu/data', imu, qos_profile_sensor_data)
node.create_subscription(State, '/mavros/state', lambda m:emit('state', dict(connected=m.connected, armed=m.armed, mode=m.mode)), qos_profile_sensor_data)
node.create_subscription(TFMessage, '/tf_static', lambda m:transform(m,'tf_static'),
    QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL))
node.create_subscription(TFMessage, '/tf', lambda m:transform(m,'tf'), qos_profile_sensor_data)
node.create_subscription(OccupancyGrid, '/map', grid,
    QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
try:
    while time.monotonic()-started < 35:
        rclpy.spin_once(node, timeout_sec=.02)
    emit('summary', dict(counts=dict(counts), duration_s=time.monotonic()-started))
finally:
    node.destroy_node()
    rclpy.shutdown()
