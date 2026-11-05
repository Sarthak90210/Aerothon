"""Replay actual recorded camera frames through the unchanged banner node."""
import json
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'src/aerothon_perception/perception_banner'))
import cv2
import rclpy
from cv_bridge import CvBridge
from perception_banner.banner_node import BannerNode

rclpy.init()
failed = False
try:
    for name in sys.argv[1:]:
        node = BannerNode()
        probe = os.environ.get('AEROTHON_BANNER_ASPECT_PROBE')
        if probe is not None:
            from rclpy.parameter import Parameter
            node.set_parameters([Parameter('min_aspect', value=float(probe))])
        sent, details = [], []
        node.pub.publish = sent.append
        node.pub_detail.publish = details.append
        node.pub_annot.publish = lambda message: None
        frame = cv2.imread(name)
        if frame is None:
            raise ValueError('Missing frame: ' + name)
        node.on_image(CvBridge().cv2_to_imgmsg(frame, encoding='bgr8'))
        detail = json.loads(details[-1].data)
        print(json.dumps({'frame': name, 'minimum_aspect': node._g('min_aspect'), **detail}))
        failed |= not detail['identified']
        node.destroy_node()
finally:
    rclpy.shutdown()
raise SystemExit(1 if failed else 0)
