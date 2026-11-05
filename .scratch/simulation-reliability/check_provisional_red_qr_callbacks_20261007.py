"""Run the existing labelled QR fixtures through the real repaired callback."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root/'src/aerothon_perception/perception_redzone'),
    str(root/'src/aerothon_perception/perception_banner'), str(root/'src/aerothon_mission/mission_bt')]
import rclpy
from geometry_msgs.msg import PoseStamped
from perception_redzone.redzone_node import RedZoneNode
from mission_bt.mav_commander import Mav
from provisional_red_entry_candidate_20261007 import install

install(RedZoneNode, Mav, root/'logs/reliability_provisional_red_qr_callback_sources_20261007')
rclpy.init()
node = RedZoneNode()
messages = []
node.pub_detail.publish = messages.append


def callback_boundaries(frame, altitude, hfov):
    node._hfov = hfov
    node._cam_pitch = 3.141592653589793/2
    pose = PoseStamped()
    pose.header.stamp = node.get_clock().now().to_msg()
    pose.pose.position.z = altitude
    pose.pose.orientation.w = 1.
    node.on_pose(pose)
    message = node.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
    message.header.stamp = pose.header.stamp
    node.on_image(message)
    import json
    detail = json.loads(messages[-1].data)
    return detail['provisional_exclusions']


template = Path(__file__).with_name('check_partial_red_qr_fixtures_20261007.py')
source = template.read_text()
old = 'found=partial_boundaries(frame,alt,hfov,project)'
assert source.count(old) == 1
source = source.replace(old, 'found=callback_boundaries(frame,alt,hfov)')
source = source.replace('reliability_partial_red_qr_fixtures_intrinsics_20261007.json', 'reliability_provisional_red_qr_callbacks_20261007.json')
source = source.replace("scope='Controlled red-ink QR image fixtures only; no flight telemetry or success evidence'",
    "scope='Existing controlled red-ink QR fixtures through actual camera callback; no flight qualification'")
try:
    exec(compile(source, str(template), 'exec'), dict(__file__=str(template), __name__='__main__', callback_boundaries=callback_boundaries))
finally:
    node.destroy_node()
    rclpy.shutdown()
