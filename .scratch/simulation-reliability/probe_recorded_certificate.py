"""Evaluate the real certificate against recorded onboard inputs only."""
import bisect,inspect,json,math,sys,textwrap
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'src/aerothon_avoidance/avoidance'))
import rclpy
from geometry_msgs.msg import PoseStamped,TransformStamped
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer
from rosidl_runtime_py.set_message import set_message_fields
from avoidance.velocity_controller import VelocityController
out=root/'logs/reliability_render_my_world_s20261003_gustfix_20261006'
boards=[json.loads(v) for v in (out/'onboard.jsonl').open()];bt=[r['stamp'] for r in boards]
scans=[json.loads(v) for v in (out/'onboard_lidar.jsonl').open()];st=[v['received_stamp'] for v in scans]
commands=[json.loads(v) for v in (out/'flight_commands.jsonl').open()]
source=textwrap.dedent(inspect.getsource(VelocityController._publish))
code=source[source.index('        def motion_clear'):source.index('        if not motion_clear')]
code=textwrap.dedent(code)
rclpy.init();node=VelocityController();node.enabled=True
mount=TransformStamped();mount.header.frame_id='base_link';mount.child_frame_id='base_scan'
mount.transform.translation.x=.138933;mount.transform.translation.y=-.002257;mount.transform.translation.z=.0815;mount.transform.rotation.w=1.
node._tf_buffer=Buffer();node._tf_buffer.set_transform_static(mount,'recorded_onboard_mount')
try:
    results=[]
    for want in (869.8,871.7,874.7,875.3,876.5):
        r=boards[bisect.bisect_left(bt,want)];now=r['stamp'];node._now=lambda:now
        scanrow=scans[bisect.bisect_right(st,now)-1];data=scanrow['data'];capture=data['header']['stamp']['sec']+data['header']['stamp']['nanosec']*1e-9
        node._pose_history.clear()
        for pr in boards[max(0,bisect.bisect_left(bt,capture)-2):bisect.bisect_right(bt,now)]:
            pose=PoseStamped();set_message_fields(pose,pr['pose']['data']);node._on_pose(pose)
        scan=LaserScan();clean=dict(data);clean['ranges']=[float(v) for v in data['ranges']];set_message_fields(scan,clean);node._on_scan(scan)
        b,rr=node.conditioned(scan);hits=rr<float(node._g('range_max_valid'))-.001;origin,b,rr=node._registered_scan(b,rr);node._planner.observe(b,rr,sensor_origin=origin,hits=hits)
        d=r['avoidance'];yaw=node._yaw;c,s=math.cos(yaw),math.sin(yaw);rotation=np.array([[c,s],[-s,c]])
        node._command_history.clear()
        for cmd in commands:
            t=cmd['stamp'];v=cmd['data']
            if now-2<t<=now and v.get('type_mask')==1479:
                q=boards[max(0,bisect.bisect_right(bt,t)-1)]['pose']['data']['pose']['orientation'];cy=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2));cv=v['velocity'];cc,ss=math.cos(cy),math.sin(cy)
                node._command_history.append((t,np.array([cc*cv['x']-ss*cv['y'],ss*cv['x']+cc*cv['y']])))
        ground=rotation@np.array(d['ground_velocity_world_mps']);wind=rotation@np.array(d['disturbance_world_mps']);wind_rate=rotation@np.array(d['disturbance_rate_world_mps2'])
        env=dict(self=node,rotation=rotation,ground=ground,wind=wind,wind_rate=wind_rate,np=np);exec(code,env)
        cmd=(d['cmd_vx'],d['cmd_vy_left']);forecast=env['motion_clear'](cmd);env['wind_rate']=np.zeros(2);steady=env['motion_clear'](cmd)
        results.append(dict(t=now,command=cmd,forecast_clear=forecast,steady_disturbance_clear=steady,clearance=d['observed_clearance_m'],rate=d['disturbance_rate_world_mps2']))
    print(json.dumps(results,indent=2))
finally:node.destroy_node();rclpy.shutdown()
