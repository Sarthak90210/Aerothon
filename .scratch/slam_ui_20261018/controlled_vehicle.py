"""Synthetic ROS display inputs with independent freshness/held-state controls."""
import importlib.util
import json
from pathlib import Path
import rclpy
from std_msgs.msg import String

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('original_ui_fixture', here.parent / 'gcs_testing_20261018' / 'fake_vehicle.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

class Gate:
    def __init__(self, publisher, channel, node):
        self.publisher, self.channel, self.node = publisher, channel, node

    def publish(self, message):
        control = self.node.control
        if control.get('pause_' + self.channel):
            return
        if self.channel == 'status' and control.get('mapping_state'):
            message = String(data=json.dumps({'source': 'LiDAR odometry', 'state': control['mapping_state'],
                                             'reason': control.get('reason', '')}))
        if self.channel == 'pose' and control.get('pose_frame'):
            message.header.frame_id = control['pose_frame']
        self.publisher.publish(message)

class ControlledVehicle(fixture.FakeVehicle):
    def __init__(self):
        self.control = {}
        super().__init__()
        for name, channel in [('p_scan', 'scan'), ('p_raw', 'scan'), ('p_map', 'map'),
                              ('p_slam_pose', 'pose'), ('p_slam', 'status')]:
            setattr(self, name, Gate(getattr(self, name), channel, self))
        self.create_timer(.1, self.read_control)

    def read_control(self):
        try:
            self.control = json.loads((here / 'fixture_control.json').read_text())
        except (OSError, ValueError):
            self.control = {}

rclpy.init()
node = ControlledVehicle()
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
    rclpy.shutdown()
