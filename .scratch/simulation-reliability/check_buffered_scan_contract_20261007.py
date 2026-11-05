"""Exercise real node subscription callbacks with controlled stamped captures."""
import hashlib,json,sys
from pathlib import Path
import rclpy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import LaserScan

root=Path(__file__).resolve().parents[2]
snapshot=root/'.scratch/buffered_scan_motion_candidate_20261007'
sys.path.insert(0,str(snapshot/'src/aerothon_avoidance/avoidance'))
from avoidance.velocity_controller import VelocityController
from avoidance.buffered_scan_pose import install
out=root/'logs/reliability_buffered_scan_contract_20261007';out.mkdir(exist_ok=False)
rclpy.init();node=VelocityController();install(node)
clock=[1.];node._now=lambda:clock[0]
checks=[]
def pose(stamp,x):
    message=PoseStamped();message.header.stamp.sec=int(stamp)
    message.header.stamp.nanosec=round((stamp-int(stamp))*1e9)
    message.pose.position.x=x;message.pose.position.z=3.;message.pose.orientation.w=1.
    return message
def scan(stamp):
    message=LaserScan();message.header.frame_id='base_link';message.header.stamp.sec=int(stamp)
    message.header.stamp.nanosec=round((stamp-int(stamp))*1e9)
    message.angle_min=-3.14;message.angle_increment=6.28/100
    message.range_min=.05;message.range_max=12.;message.ranges=[4.]*100
    return message
try:
    pose_subscription=next(sub for sub in node.subscriptions if sub.callback==node._on_pose)
    scan_subscription=next(sub for sub in node.subscriptions if sub.callback==node._on_scan)
    pose_subscription.callback(pose(1.,0.));first=scan(1.)
    scan_subscription.callback(first);assert node.scan is first
    checks.append('real subscription callbacks select an exactly paired capture')
    clock[0]=1.1;pending=scan(1.1);scan_subscription.callback(pending)
    assert node.scan is first and node._pending_paired_scan[1] is pending
    assert not node.scan_stale()
    checks.append('unbracketed capture retains the previous paired scan while fresh')
    clock[0]=1.2;pose_subscription.callback(pose(1.2,.2))
    assert node.scan is pending and node._pending_paired_scan is None
    assert abs(node._scan_pose[0]-.1)<1e-8
    checks.append('arrival of the later pose promotes the capture with interpolated pose')
    node._on_scan(scan(1.05));assert node.scan is pending
    assert node._pending_paired_scan is None
    checks.append('replayed captures cannot replace the selected scan')
    clock[0]=1.25;node._on_scan(scan(1.5));node._on_scan(scan(1.4))
    assert node._pending_paired_scan[0]==1.5
    clock[0]=1.6;node._on_pose(pose(1.6,.6))
    assert node.scan is pending and node.scan_stale()
    checks.append('oversized pose gaps never extrapolate or keep stale scans fresh')
    node.enabled=True;node.state='CRUISE';node._tick()
    assert node.last_detail['cmd_vx']==0 and node.last_detail['cmd_vy_left']==0
    assert 'stale' in node.last_detail.get('fault','')
    checks.append('stale selected scan produces an actual stopped controller command')
    node._on_scan(scan(-1.));assert node.scan is None and node._scan_t is None
    checks.append('invalid capture stamp invalidates the active scan')
finally:
    node.destroy_node();rclpy.shutdown()
report=dict(passed=True,checks=checks,scope='Controlled ROS callback contract; not flight qualification',
    module_sha256=hashlib.sha256((snapshot/'src/aerothon_avoidance/avoidance/avoidance/buffered_scan_pose.py').read_bytes()).hexdigest(),
    production_adopted=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,checks=len(checks))))
