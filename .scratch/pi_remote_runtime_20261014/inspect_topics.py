import json,time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from nav_msgs.msg import OccupancyGrid

rclpy.init();node=rclpy.create_node('runtime_input_inspection');found={}
def scan(m):found['scan']={'frame':m.header.frame_id,'stamp':m.header.stamp.sec+m.header.stamp.nanosec/1e9,'count':len(m.ranges)}
def pose(m):found['pose']={'frame':m.header.frame_id,'stamp':m.header.stamp.sec+m.header.stamp.nanosec/1e9}
node.create_subscription(LaserScan,'/scan',scan,qos_profile_sensor_data)
node.create_subscription(PoseStamped,'/mavros/local_position/pose',pose,qos_profile_sensor_data)
for topic in ['/camera/pose_state','/winch/status','/mission_ready/detail']:
 node.create_subscription(String,topic,lambda m,k=topic:found.update({k:json.loads(m.data)}),10)
node.create_subscription(OccupancyGrid,'/map',lambda m:found.update({'map':{'frame':m.header.frame_id,'w':m.info.width,'h':m.info.height}}),1)
end=time.monotonic()+6
while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
found['clock']=node.get_clock().now().nanoseconds/1e9
print(json.dumps(found));node.destroy_node();rclpy.try_shutdown()
