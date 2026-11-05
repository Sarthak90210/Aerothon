"""Actual ROS delivery during a slow control callback, without flight claims."""
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import threading
import time

root = Path(__file__).resolve().parents[2]
snapshot = root/'.scratch/command_deadline_candidate_20261007'
sys.path.insert(0, str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance import velocity_controller
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, TwistStamped
from sensor_msgs.msg import LaserScan
from rclpy.qos import qos_profile_sensor_data

mode = sys.argv[1]
out = root/f'logs/reliability_capture_callback_starvation_{mode}_20261007.json'
assert not out.exists()
spec = importlib.util.spec_from_file_location('capture_candidate', Path(__file__).with_name('capture_inbox_candidate_20261007.py'))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
ages = []
def slow_tick(node):
    now = time.time()
    if node._pose_t is not None and now-started > 2.:
        ages.append(now-node._pose_t)
    # Model a 120 ms planner callback. Only callback scheduling is under test;
    # there is no aircraft, simulated dynamics or fabricated flight result.
    time.sleep(.12)
velocity_controller.VelocityController._tick = slow_tick
rclpy.init()
node = velocity_controller.VelocityController()
sender = Node('controlled_onboard_capture_sender')
pose_pub = sender.create_publisher(PoseStamped, '/mavros/local_position/pose', qos_profile_sensor_data)
velocity_pub = sender.create_publisher(TwistStamped, '/mavros/local_position/velocity_local', qos_profile_sensor_data)
scan_pub = sender.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
stop = threading.Event()
started = time.time()
def send():
    sequence = 0
    while not stop.is_set():
        pose = PoseStamped()
        pose.header.stamp = sender.get_clock().now().to_msg()
        pose.pose.position.z = 3.
        pose.pose.orientation.w = 1.
        velocity = TwistStamped()
        velocity.header.stamp = pose.header.stamp
        scan = LaserScan()
        scan.header.stamp = pose.header.stamp
        scan.header.frame_id = 'base_link'
        scan.angle_min = -math.pi
        scan.angle_increment = 2*math.pi/500
        scan.range_min, scan.range_max = .05, 12.
        scan.ranges = [12.]*500
        pose_pub.publish(pose)
        velocity_pub.publish(velocity)
        if sequence % 5 == 0:
            scan_pub.publish(scan)
        sequence += 1
        stop.wait(.02)
worker = threading.Thread(target=send)
inbox = candidate.CaptureInbox(node) if mode == 'inbox' else None
executor = SingleThreadedExecutor()
executor.add_node(node)
worker.start()
try:
    while time.time()-started < 7.:
        executor.spin_once(timeout_sec=.1)
finally:
    stop.set()
    worker.join(2.)
    executor.shutdown(timeout_sec=2.)
    if inbox:
        inbox.close()
    node.destroy_node()
    sender.destroy_node()
    rclpy.shutdown()
assert len(ages) >= 10, ages
report = dict(mode=mode, captures=len(ages), median_age_s=statistics.median(ages),
    max_age_s=max(ages), all_ages_s=ages, production_modified=False,
    scope='Actual ROS callback-scheduling diagnostic with controlled inputs; no motion or flight qualification')
with out.open('x') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({key:value for key,value in report.items() if key != 'all_ages_s'}))
