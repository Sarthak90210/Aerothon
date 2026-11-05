"""Passive camera/FCU observation, with no flight or simulator-truth commands."""
import json,time
from pathlib import Path
import rclpy,cv2
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image,CameraInfo
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from cv_bridge import CvBridge
from rosidl_runtime_py.convert import message_to_ordereddict
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_split_banner_camera_review_20261007';out.mkdir(exist_ok=False)
rclpy.init();node=Node('passive_banner_camera_review',parameter_overrides=[Parameter('use_sim_time',value=True)])
data={};bridge=CvBridge()
def record(key,msg):data[key]=message_to_ordereddict(msg)
def camera(msg):
    if 'image' not in data:
        data['image']=msg;data['image_received_clock_s']=node.get_clock().now().nanoseconds*1e-9
node.create_subscription(Image,'/camera/image',camera,qos_profile_sensor_data)
node.create_subscription(CameraInfo,'/camera_info',lambda m:record('camera_info',m),qos_profile_sensor_data)
node.create_subscription(PoseStamped,'/mavros/local_position/pose',lambda m:record('pose',m),qos_profile_sensor_data)
node.create_subscription(String,'/camera/state',lambda m:record('camera_state',m),10)
node.create_subscription(String,'/percep/banner/detail',lambda m:record('banner',m),10)
deadline=time.monotonic()+12
try:
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.1)
        if all(k in data for k in ('image','camera_info','pose','camera_state','banner')):break
    assert 'image' in data,'No actual camera frame received'
    msg=data.pop('image')
    assert cv2.imwrite(str(out/'camera.png'),bridge.imgmsg_to_cv2(msg,'bgr8'))
    data['image_header']=message_to_ordereddict(msg.header)
    data.update(scope='Passive onboard camera and FCU data only; no simulator geometry, contact or attachment data',
                subscriptions=['/camera/image','/camera_info','/mavros/local_position/pose','/camera/state','/percep/banner/detail'],
                flight_commands_sent=False,paired_capture_time_claim=False)
    (out/'observation.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(dict(image=str(out/'camera.png'),fields=list(data),commands_sent=False)))
finally:node.destroy_node();rclpy.shutdown()
