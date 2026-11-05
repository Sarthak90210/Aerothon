"""Native ROS/slam_toolbox integration with recorded synthetic scans, no FCU/GPS."""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tempfile
import shutil

import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from lifecycle_msgs.srv import ChangeState
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import StaticTransformBroadcaster

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src/aerothon_mission/mission_bringup'))
os.environ.update(ROS_DOMAIN_ID='87',ROS_LOCALHOST_ONLY='1',ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',ROS_LOG_DIR=str(OUT/'roslogs'))
os.environ['PYTHONPATH']=str(ROOT/'src/aerothon_mission/mission_bringup')+os.pathsep+os.environ.get('PYTHONPATH','')
children=[];handles=[]
adapter_directory=tempfile.TemporaryDirectory(prefix='aerothon-grid-test-')


def spawn(command,name):
    log=open(OUT/(name+'.log'),'w');handles.append(log)
    env=dict(os.environ)
    if name=='slam_toolbox':
        adapter=OUT/'colcon_install/aerothon_slam_grid/lib/libaerothon_slam_grid.so'
        assert adapter.is_file(),'build the grid-bounds adapter first'
        clean_path=Path(adapter_directory.name)/adapter.name
        shutil.copy2(adapter,clean_path)
        env['LD_PRELOAD']=str(clean_path)
    p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=env)
    children.append(p)


def rays(pose):
    a=np.linspace(-math.pi,math.pi,720,endpoint=False)+pose[2]
    dx,dy=np.cos(a),np.sin(a);dist=np.full(720,np.inf)
    for x in (-4.,5.):
        t=(x-pose[0])/np.where(abs(dx)>1e-9,dx,np.nan);y=pose[1]+t*dy
        use=(t>0)&(y>=-3)&(y<=4);dist[use]=np.minimum(dist[use],t[use])
    for y in (-3.,4.):
        t=(y-pose[1])/np.where(abs(dy)>1e-9,dy,np.nan);x=pose[0]+t*dx
        use=(t>0)&(x>=-4)&(x<=5);dist[use]=np.minimum(dist[use],t[use])
    # Deterministic 2 mm range perturbation exercises raster boundary cells and
    # avoids a perfect zero-noise room ending exactly on the grid's upper edge.
    return (dist + np.random.default_rng(17).normal(0,.002,720)).tolist()


rclpy.init();node=Node('mapping_integration_observer')
maps=[];statuses=[]
node.create_subscription(OccupancyGrid,'/map',lambda m:maps.append(m),QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
node.create_subscription(String,'/slam/status',lambda m:statuses.append(json.loads(m.data)),10)
publisher=node.create_publisher(LaserScan,'/scan',qos_profile_sensor_data)
tf=StaticTransformBroadcaster(node);mount=TransformStamped()
mount.header.frame_id='base_link';mount.child_frame_id='base_scan';mount.transform.rotation.w=1.
mount.header.stamp=node.get_clock().now().to_msg();tf.sendTransform(mount)

def publish_scan(pose):
    scan=LaserScan();scan.header.frame_id='base_scan';scan.header.stamp=node.get_clock().now().to_msg()
    scan.angle_min=-math.pi;scan.angle_increment=2*math.pi/720
    scan.angle_max=scan.angle_min+719*scan.angle_increment;scan.range_min=.05;scan.range_max=12.
    scan.scan_time=.1;scan.time_increment=.1/720;scan.ranges=rays(pose)
    publisher.publish(scan)
    deadline=time.monotonic()+.1
    while time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.01)
try:
    spawn([sys.executable,'-c','from mission_bringup.scan_odometry import main; main()'],'mapping_odometry')
    spawn(['/opt/ros/jazzy/lib/slam_toolbox/async_slam_toolbox_node','--ros-args',
           '-p','odom_frame:=lidar_odom','-p','base_frame:=lidar_mapping_base',
           '-p','map_frame:=map','-p','scan_topic:=/scan_slam','-p','resolution:=0.05',
           '-p','max_laser_range:=12.0','-p','map_update_interval:=0.5',
           '-p','minimum_travel_distance:=0.1','-p','minimum_travel_heading:=0.1',
           '-p','min_pass_through:='+os.environ.get('AEROTHON_NATIVE_MIN_PASS','1'),
           '-p','minimum_time_interval:=0.1','-p','transform_timeout:=0.3'], 'slam_toolbox')
    client=node.create_client(ChangeState,'/slam_toolbox/change_state')
    assert client.wait_for_service(timeout_sec=15),'slam_toolbox lifecycle service missing'
    for transition in (1,3):
        request=ChangeState.Request();request.transition.id=transition
        future=client.call_async(request);rclpy.spin_until_future_complete(node,future,timeout_sec=10)
        assert future.done() and future.result().success,'slam_toolbox lifecycle transition failed'
    for _ in range(50):
        publish_scan((0,0,0))
        if statuses and statuses[-1]['state']=='Tracking':break
    assert statuses and statuses[-1]['state']=='Tracking','mapping never acquired initial scene'
    statuses.clear();maps.clear()
    for i in range(120):
        t=max(0,i-20)*.01
        pose=(.4*math.sin(t),.2*math.sin(t*.7),.06*math.sin(t))
        publish_scan(pose)
    assert maps,'native SLAM produced no map without GPS'
    g=maps[-1];data=np.array(g.data).reshape(g.info.height,g.info.width)
    yy,xx=np.nonzero(data>=65)
    x=g.info.origin.position.x+(xx+.5)*g.info.resolution
    y=g.info.origin.position.y+(yy+.5)*g.info.resolution
    error=np.minimum.reduce((abs(x+4),abs(x-5),abs(y+3),abs(y-4)))
    fraction=float(np.mean(error<=.12))
    free_fraction=float(np.mean(data[10:-10,10:-10]==0))
    tracking=sum(s['state']=='Tracking' for s in statuses)
    from scipy.spatial import cKDTree
    wall_samples=np.concatenate((np.c_[np.linspace(-3.8,4.8,150),np.full(150,-3.)],
                                 np.c_[np.linspace(-3.8,4.8,150),np.full(150,4.)],
                                 np.c_[np.full(120,-4.),np.linspace(-2.8,3.8,120)],
                                 np.c_[np.full(120,5.),np.linspace(-2.8,3.8,120)]))
    wall_coverage=float(np.mean(cKDTree(np.c_[x,y]).query(wall_samples)[0]<.15))
    result=dict(kind='native ROS synthetic-scan integration, no FCU/GPS',map_messages=len(maps),tracking_scans=tracking,
                scans=120,resolution_m=g.info.resolution,width=g.info.width,height=g.info.height,
                occupied_cells=len(xx),occupied_within_120mm_of_wall=fraction,
                interior_free_fraction=free_fraction,
                wall_coverage_within_150mm=wall_coverage, synthetic_range_noise_m=.002,
                held_reasons=sorted(set(s['reason'] for s in statuses if s['state']!='Tracking')),
                hardware_qualified=False,pass_check=bool(tracking>=90 and fraction>=.95 and wall_coverage>=.95 and free_fraction>=.95))
    (OUT/'browser_fixture.json').write_text(json.dumps(dict(grid=dict(w=g.info.width,h=g.info.height,res=g.info.resolution,
        ox=g.info.origin.position.x,oy=g.info.origin.position.y,yaw=0,frame='map',stamp=time.time(),data=list(g.data)),
        scan=dict(angle_min=-math.pi,angle_step=2*math.pi/720,ranges=rays((0,0,0)),range_min=.05,range_max=12))))
    (OUT/'native_slam.json').write_text(json.dumps(result,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,7))
    ax.imshow(np.where(data<0,.5,1-data/100),origin='lower',cmap='gray',vmin=0,vmax=1,
              extent=(g.info.origin.position.x,g.info.origin.position.x+g.info.width*g.info.resolution,
                      g.info.origin.position.y,g.info.origin.position.y+g.info.height*g.info.resolution))
    ax.set(xlabel='Local X, m',ylabel='Local Y, m',title='Native SLAM from synthetic lidar scans, no GPS')
    ax.set_aspect('equal');fig.tight_layout();fig.savefig(OUT/'native_slam.png',dpi=150);plt.close(fig)
    print(json.dumps(result),flush=True)
    assert result['pass_check'],'native SLAM geometry check failed'
finally:
    for child in reversed(children):
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGINT)
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5)
    for handle in handles:handle.close()
    adapter_directory.cleanup()
    node.destroy_node();rclpy.shutdown()
