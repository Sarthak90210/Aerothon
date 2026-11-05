"""Capture one actual decision-classified image matched by camera timestamp."""
from collections import OrderedDict
import json,time
from pathlib import Path
import cv2,rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_split_pristine_alignment_frame_20261007';out.mkdir(exist_ok=False)
rclpy.init();node=Node('passive_pristine_alignment_frame',parameter_overrides=[Parameter('use_sim_time',value=True)])
images=OrderedDict();pending={};selected=[]
def match():
    for stamp,detail in list(pending.items()):
        if stamp in images and not selected:
            selected.append((images[stamp],detail,node.get_clock().now().nanoseconds*1e-9))
def image(message):
    stamp=message.header.stamp.sec*1000000000+message.header.stamp.nanosec
    images[stamp]=message
    while len(images)>30:images.popitem(last=False)
    match()
def detail(message):
    value=json.loads(message.data);box=value.get('board_px');iw,ih=(value.get('image_wh') or [1280,720])[:2]
    if not value.get('identified') or not box:return
    capture=value.get('capture_stamp')
    if not isinstance(capture,(int,float)):return
    pending[round(capture*1e9)]=value
    if len(pending)>30:pending.pop(next(iter(pending)))
    match()
node.create_subscription(Image,'/camera/image',image,qos_profile_sensor_data)
node.create_subscription(String,'/percep/banner/detail',detail,10)
deadline=time.monotonic()+40
try:
    while time.monotonic()<deadline and not selected:rclpy.spin_once(node,timeout_sec=.1)
    if selected:
        message,value,received=selected[0]
        assert cv2.imwrite(str(out/'camera.png'),CvBridge().imgmsg_to_cv2(message,'bgr8'))
        report=dict(captured=True,capture_stamp=value['capture_stamp'],received_clock=received,
            image_header_stamp=dict(sec=message.header.stamp.sec,nanosec=message.header.stamp.nanosec),detail=value,
            exact_capture_timestamp_match=True,flight_commands_sent=False,simulator_truth_subscribed=False,
            scope='Actual onboard image and matching detector classification; not a false-positive verdict')
    else:report=dict(captured=False,scope='No eligible classification observed during bounded passive capture')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(captured=report['captured'],path=str(out))))
finally:node.destroy_node();rclpy.shutdown()
