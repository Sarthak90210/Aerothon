"""Actual gate leaf and streamed lidar guard with normal-response airframe.

Recorded estimator error is replayed; scan noise is regenerated. This is a
diagnostic seam, not a reconstruction of ROS scheduling or qualification.
"""
import csv,json,math,sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import py_trees
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import LaserScan
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_headless_land_position_hold import world
from headless_world import Arena,DT,WindDrift,W,LidarCorruptor
from mission_bt.mav_commander import Mav
from mission_bt.gate_braking import BrakedGateAdvance


def replay(brake_gain=0.,motion_arrival=False):
 run=root/'logs/reliability_reduced_v28_targeted_20261008/my_world_random_s3'
 rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
 truths=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
 start=min((r for r in rows if r.get('pose')),key=lambda r:abs(r['stamp']-749.))
 truth=min(truths,key=lambda r:abs(float(r['t_sim'])-start['stamp']))
 w=world();w.t=start['stamp'];epoch=w.t;w.p=np.array([float(truth[k]) for k in ['x','y','z']])
 p=start['pose']['data']['pose'];q=p['orientation'];w.yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
 cond=json.loads((run/'run.json').read_text())['conditions'];wind=cond['wind']
 w.arena=Arena(W.load(run/'world_spec.json'),'b')
 w.wind=WindDrift(mean=wind['speed'],gust=wind['gust'],period=wind['gust_period_s'],dir_rad=math.radians(wind['dir_deg']),turb=.5*wind['veer_deg']/20*wind['speed']/8,seed=3,dt=DT)
 for i in range(round(epoch/DT)):w.wind(i*DT)
 v=start['velocity']['data']['twist']['linear'];w.ground_velocity=np.array([v[k] for k in ['x','y','z']]);w.v=w.ground_velocity.copy();w.v[:2]-=np.array(w.wind(epoch));w.speed_cap=5.
 tt=np.array([float(r['t_sim']) for r in truths]);tx=np.array([[float(r[k]) for k in ['x','y','z']] for r in truths]);samples=[]
 for r in rows:
  if epoch-.2<=r['stamp']<=epoch+61 and r.get('pose'):
   est=r['pose']['data']['pose']['position'];truth=np.array([np.interp(r['stamp'],tt,tx[:,k]) for k in range(3)])
   samples.append((r['stamp'],np.array([est[k] for k in ['x','y','z']])-truth))
 et=np.array([t for t,e in samples]);errors=np.array([e for t,e in samples])
 mav=Mav.__new__(Mav);mav.node=NS(get_clock=lambda:NS(now=lambda:NS(nanoseconds=round(w.t*1e9),to_msg=w.stamp)))
 mav._sp=None;mav._scan=None;mav._scan_t=None;mav.keepout_m=1.;mav.keepout_events=0;mav._keepout_on=False
 mav.pose=PoseStamped();mav.delivery_inputs={};mav.speed_cmd=5.;mav.exclusions=[];mav._avoiding=False
 mav.enable_avoidance=lambda *args,**kwargs:None;mav.log=lambda *args,**kwargs:None
 mav._track_altitude_error=lambda:None;mav.state=NS(armed=True);mav.setpoints_suppressed=0
 def publish(message):
  p=message.pose.position;q=message.pose.orientation;yaw=math.atan2(2*q.w*q.z,1-2*q.z*q.z)
  w.sp_pos=(p.x,p.y,p.z,yaw);w.sp_vel=None
 mav.pub_sp=NS(publish=publish)
 def speed_request(speed):
  mav.speed_cmd=w.speed_cap=speed
  return NS(done=lambda:True,result=lambda:NS(success=True))
 mav.set_speed=speed_request
 lidar=LidarCorruptor(cond['lidar'],seed=4);leaf=BrakedGateAdvance(mav,tol=.25,gate_speed_mps=.35,restore_speed_mps=5.)
 leaf.initialise();leaf._target=(14.89813394656775,-15.884451067649756);leaf._flight_alt=2.7701346731707823;leaf._flight_distance=6.509
 changes=[];previous=None;progress=np.zeros(2);previous_motion=None;pending_motion=deque();axis=np.array([math.cos(w.yaw),math.sin(w.yaw)])
 if motion_arrival:
  from unittest.mock import patch
  from mission_bt.mission_tree import GateAdvance
  original=GateAdvance.update
  def measured_arrival(self):
   if float(progress@axis)>=self._flight_distance-self.tol:return py_trees.common.Status.SUCCESS
   return original(self)
  patcher=patch.object(GateAdvance,'update',measured_arrival);patcher.start()
 if brake_gain:
  def brake_position():
   x,y,z=leaf._brake_hold;d=mav.delivery_inputs
   mav.goto(x-brake_gain*d['vx'],y-brake_gain*d['vy'],z,leaf._brake_yaw)
  leaf._brake_position=brake_position
 minimum=float('inf');status=py_trees.common.Status.RUNNING;next_pose=next_scan=next_stream=next_tick=epoch
 for _ in range(6201):
  e=np.array([np.interp(w.t,et,errors[:,k]) for k in range(3)]);w.gps_err=e[:2];w.baro_err=e[2];est=w.est()
  if w.t>=next_pose:
   mav.pose.pose.position.x,mav.pose.pose.position.y,mav.pose.pose.position.z=map(float,est)
   mav.pose.pose.orientation.z=math.sin(w.yaw/2);mav.pose.pose.orientation.w=math.cos(w.yaw/2)
   mav.delivery_inputs.update(pose_stamp=w.t,velocity_stamp=w.t,speed=float(np.linalg.norm(w.ground_velocity[:2])),vx=float(w.ground_velocity[0]),vy=float(w.ground_velocity[1]));next_pose=w.t+.03-1e-9
   pending_motion.append((w.t,w.ground_velocity[:2].copy()))
  if w.t>=next_scan:
   ranges=w.arena.raycast(*w.p[:2],w.p[2]+.08,w.yaw);scan=LaserScan();scan.header.stamp=w.stamp();scan.angle_min=-math.pi;scan.angle_increment=2*math.pi/len(ranges);scan.range_min=.05;scan.range_max=12.;scan.ranges=list(map(float,lidar.apply(ranges,.05,12.)))
   mav._on_scan(scan);next_scan=w.t+.1-1e-9
  if w.t>=next_tick:
   while pending_motion:
    sample=pending_motion.popleft()
    if previous_motion is not None:
     progress+=(sample[0]-previous_motion[0])*.5*(sample[1]+previous_motion[1])
    previous_motion=sample
   status=leaf.update();next_tick=w.t+.2-1e-9
   if leaf._phase!=previous:changes.append((w.t,leaf._phase));previous=leaf._phase
   if status is not py_trees.common.Status.RUNNING:break
  if w.t>=next_stream:mav._stream();next_stream=w.t+.1-1e-9
  w.t+=DT;w._step_airframe()
  minimum=min(minimum,min(W.distance_to_edge(w.p[:2],poly) for poly,z0,z1,kind in w.arena.boxes if kind in ['wall','obstacle'] and z0<=w.p[2]<=z1))
 if motion_arrival:patcher.stop()
 return dict(status=str(status),phase=leaf._phase,phase_changes=changes,motion_progress_m=float(progress@axis),seconds=w.t-epoch,minimum_clearance_m=minimum,contacts=w.contacts,reason=leaf.feedback_message,actual_position=w.p.tolist(),estimated_position=est.tolist(),target=leaf._target,normal_response_s=.6,extra_queue_s=0.,limitation='Recorded estimator error, regenerated scans; no ROS arrival ordering; diagnostic only')


def test_recorded_gate_entry_finishes_without_contact_or_clearance_loss():
 result=replay();(root/'logs/reliability_recorded_gate_physics_baseline_20261008.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 assert result['status']=='Status.SUCCESS'
 assert not result['contacts']
 assert result['minimum_clearance_m']>=.70
