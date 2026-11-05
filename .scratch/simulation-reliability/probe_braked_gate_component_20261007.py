"""Focused GateAdvance component using the current headless physics methods.

Arena geometry supplies physical lidar and independent grading only. The
mission leaf receives the onboard scan, pose and ground velocity, never boxes.
This is a new deterministic component case, not an exact replay of DDS timing.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
from types import MethodType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'sim'))
import headless_world as H
import numpy as np
from geometry_msgs.msg import PoseStamped, TwistStamped
from sensor_msgs.msg import LaserScan
from mission_bt.mav_commander import Mav as MavCommander
from gate_advance_braking_candidate_20261007 import BrakedGateAdvance as GateAdvance
import py_trees

p = argparse.ArgumentParser()
p.add_argument('--mode', choices=('braked_candidate',), required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--cap', type=float, default=.35)
a = p.parse_args()
assert .05 <= a.cap <= 5.
assert not a.out.exists()
sources = ('sim/headless_world.py',
    'src/aerothon_mission/mission_bt/mission_bt/mission_tree.py',
    'src/aerothon_mission/mission_bt/mission_bt/mav_commander.py',
    'src/aerothon_mission/mission_bt/mission_bt/leg_router.py',
    'sim/worlds/my_world.json', str(Path(__file__).relative_to(ROOT)))
source_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
spec = H.W.load(ROOT/'sim/worlds/my_world.json')
arena = H.Arena(spec, 'b')
world = SimpleNamespace(
    t=0., p=np.array([20.1210346123,-16.2541993250,2.176587569]),
    v=np.zeros(3), ground_velocity=np.zeros(3),
    yaw=2*math.atan2(.9956099700450008,.09359907877213543),
    args=SimpleNamespace(vel_command_delay_s=.4,vel_response_s=.6),
    gps_err=np.zeros(2),glitch=np.zeros(2),baro_err=0.,baro_noise=0.,
    armed=True, mode='GUIDED', sp_pos=None, sp_vel=None,
    pending_velocity=deque(maxlen=512), takeoff_alt=None,
    speed_cap=H.WPNAV_SPEED, params={}, fence_poly=None,
    landed_t=None, contacts=[], fence_breaches=0,
    arena=arena, wind=None, lock=threading.Lock(), events=[])
for name in ('est','_desired_velocity','_to_point','_step_airframe',
             '_on_sp_pos','_on_sp_raw','_srv_command'):
    setattr(world,name,MethodType(getattr(H.HeadlessWorld,name),world))
world._event = lambda msg:world.events.append(dict(stamp=world.t,message=msg))

class Mav:
    _delivery_velocity = MavCommander._delivery_velocity
    _nearest_return = MavCommander._nearest_return
    _kept_out = MavCommander._kept_out
    _on_scan = MavCommander._on_scan
    def __init__(self):
        self.speed_cmd=world.speed_cap
        self.delivery_inputs={}
        self.pending_speed=[]
        self.speed_acks=[]
        self.node=SimpleNamespace(get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=round(world.t*1e9))))
        self._scan=None;self._scan_t=None
        self.keepout_m=1.;self._keepout_on=False;self.keepout_events=0
        self.exclusions=[];self.gate_crossing=None;self.abort_reason=''
        self.logs=[];self.commands=[];self.request=None
    def pos(self):return tuple(float(v) for v in world.est())
    def alt(self):return self.pos()[2]
    def yaw(self):return float(world.yaw)
    def scan_age_s(self):return None if self._scan_t is None else world.t-self._scan_t
    def log(self,message,**kw):self.logs.append(dict(stamp=world.t,message=message))
    def enable_avoidance(self,on,**kw):pass
    def reached(self,x,y,z,tol):return math.dist(self.pos(),(x,y,z))<=tol
    def goto(self,x,y,z,yaw=0.):self.request=(float(x),float(y),float(z),float(yaw))
    def stream(self):
        if self.request is None:return
        x,y,z,yaw=self.request
        sp=PoseStamped()
        sp.header.stamp.sec=int(world.t);sp.header.stamp.nanosec=round((world.t-int(world.t))*1e9)
        sp.header.frame_id='map'
        sp.pose.position.x=x;sp.pose.position.y=y;sp.pose.position.z=z
        sp.pose.orientation.z=math.sin(yaw/2);sp.pose.orientation.w=math.cos(yaw/2)
        sp=self._kept_out(sp)
        world._on_sp_pos(sp)
        self.commands.append(dict(stamp=world.t,target=[sp.pose.position.x,sp.pose.position.y,sp.pose.position.z],speed_cap=world.speed_cap))
    def set_speed(self, value):
        from mavros_msgs.srv import CommandLong
        future=SimpleNamespace(done=lambda:False,result=lambda:None)
        request=CommandLong.Request();request.command=178
        request.param1=1.;request.param2=float(value);request.param3=-1.
        self.speed_cmd=float(value)
        self.pending_speed.append((world.t+.4,request,future))
        return future
    def process_speed(self):
        while self.pending_speed and self.pending_speed[0][0]<=world.t+1e-9:
            due,request,future=self.pending_speed.pop(0)
            response=world._srv_command(request,SimpleNamespace(success=False,result=0))
            future.done=lambda:True
            future.result=lambda response=response:response
            self.speed_acks.append(dict(stamp=world.t,requested_cap=request.param2,
                success=response.success))
    def observe(self):
        r=arena.raycast(*world.p[:2],world.p[2]+H.LIDAR_ABOVE_BODY_M,world.yaw)
        s=LaserScan();s.header.frame_id='base_link'
        s.header.stamp.sec=int(world.t);s.header.stamp.nanosec=round((world.t-int(world.t))*1e9)
        s.angle_min=-math.pi;s.angle_increment=2*math.pi/len(r)
        s.range_min=.05;s.range_max=12.;s.ranges=[float(v) for v in r]
        self._on_scan(s)
        self.delivery_inputs.update(pose_stamp=world.t)
        velocity=TwistStamped();velocity.header=s.header
        velocity.twist.linear.x=float(world.ground_velocity[0])
        velocity.twist.linear.y=float(world.ground_velocity[1])
        velocity.twist.linear.z=float(world.ground_velocity[2])
        self._delivery_velocity(velocity)

mav=Mav()
leaf=GateAdvance(mav, gate_speed_mps=a.cap, advance_m=4.45,alt=2.081541839765747,tol=.25,
                 clearance_m=1.5,exclusions=lambda:mav.exclusions)
leaf.initialise()
rows=[];handover=None;minimum=float('inf');first_breach=None
for step in range(6000):
    world.t=step*H.DT
    mav.process_speed()
    if step%10==0:
        mav.observe()
        if handover is None:
            status=leaf.update()
            if status==py_trees.common.Status.SUCCESS:
                speed=float(np.linalg.norm(world.ground_velocity[:2]))
                if a.mode in ('arrival_only','early_speed') and speed>.08:
                    leaf.router.fly(mav,*leaf._target,leaf._flight_alt,mav.yaw())
                else:
                    handover=dict(stamp=world.t,pose=mav.pos(),ground_velocity=world.ground_velocity.tolist(),speed=speed)
                    mav.request=None
            elif status==py_trees.common.Status.FAILURE:
                break
        mav.stream()
    if handover is not None and step%5==0:
        world._on_sp_raw(SimpleNamespace(velocity=SimpleNamespace(x=0.,y=0.,z=0.),yaw_rate=0.,coordinate_frame=9))
    world._step_airframe()
    # Independent grading sees every physical step, including before receipt.
    gaps=[0. if H.W.point_in_polygon(world.p[:2],poly) else H.W.distance_to_edge(world.p[:2],poly)
          for poly,z0,z1,kind in arena.boxes
          if z0<=world.p[2]+H.BODY_ABOVE_M and z1>=world.p[2]-H.BODY_BELOW_M]
    actual=min(gaps)
    minimum=min(minimum,actual)
    if actual<.7 and first_breach is None:first_breach=dict(stamp=world.t+H.DT,pose=world.p.tolist(),clearance=actual)
    if step%10==0:
        rows.append(dict(stamp=world.t,pose=world.p.tolist(),ground_velocity=world.ground_velocity.tolist(),actual_clearance_m=actual,speed_cap=world.speed_cap,position_owner=world.sp_pos is not None))
    if handover is not None and world.t>=handover['stamp']+3.:break
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in source_hashes.items())
result=dict(mode=a.mode,scope='Actual GateAdvance and headless physical methods, component diagnostics only; original DDS timing and noisy estimator replay are not reproduced',
    source_sha256=source_hashes,command_delay_s=.4,response_s=.6,world_source_spec='sim/worlds/my_world.json',
    gate_heading_rad=2*math.atan2(.9956099700450008,.09359907877213543),
    declared_advance_m=4.45,actual_latched_target=leaf._target,
    early_cap_mps=a.cap,speed_acks=mav.speed_acks,
    candidate_source_sha256=hashlib.sha256(Path(__file__).with_name('gate_advance_braking_candidate_20261007.py').read_bytes()).hexdigest(),
    speed_service_delay_assumption_s=.4,arrival_speed_limit_mps=.08,
    minimum_actual_clearance_m=minimum,first_breach=first_breach,handover=handover,
    passed=handover is not None and minimum>=.7,rows=rows,commands=mav.commands,
    logs=mav.logs,physical_events=world.events)
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','commands','logs','physical_events','source_sha256')}))
raise SystemExit(0 if result['passed'] else 1)
