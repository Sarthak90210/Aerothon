"""Update centred synthetic lidar fixtures to provide their assumed pose."""
import re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
frame=root/'sim/test_frame_conventions.py'
text=frame.read_text()
marker='class FrameConventionTests('
helper='''def refresh_pose(node):
    """The centred raycast fixture supplies a pose at each capture."""
    from geometry_msgs.msg import PoseStamped
    m=PoseStamped()
    now=node._now()
    m.header.stamp.sec=int(now)
    m.header.stamp.nanosec=int((now-int(now))*1e9)
    x,y=node._pos or (0.0,0.0)
    m.pose.position.x,m.pose.position.y=float(x),float(y)
    m.pose.position.z=float(node._alt or 3.0)
    yaw=node._yaw or 0.0
    m.pose.orientation.z=math.sin(yaw/2)
    m.pose.orientation.w=math.cos(yaw/2)
    node._on_pose(m)


'''
assert marker in text
text=text.replace(marker,helper+marker,1)
text=re.sub(r'^(\s*)self.node._on_scan\(',lambda m:m[1]+'refresh_pose(self.node)\n'+m[1]+'self.node._on_scan(',text,flags=re.M)
frame.write_text(text)
path=root/'sim/test_corridor_recovery.py'
text=path.read_text().replace('from test_frame_conventions import make_scan','from test_frame_conventions import make_scan, refresh_pose')
assert text.count('scan = LaserScan()')==2
text=text.replace('scan = LaserScan()','scan = LaserScan()\n    scan.header.frame_id = "base_link"')
text=re.sub(r'^(\s*)self.node._on_scan\(',lambda m:m[1]+'refresh_pose(self.node)\n'+m[1]+'self.node._on_scan(',text,flags=re.M)
text=text.replace('m = PoseStamped()','m = PoseStamped()\n        m.pose.orientation.w = 1.0')
path.write_text(text)
