"""Recorded landing entry/error, real camera/descent/airframe; no ROS ordering."""
import csv,json,math,random,sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import py_trees
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'sim'),str(root/'.scratch/simulation-reliability')]
from test_precision_descent_physics_seam_20261008 import CameraAirframe
from headless_world import DT,WindDrift,CAMERA_KEYS
from mission_bt.mission_tree import PrecisionDescent

def replay(gain=None, recorded_pose=False):
 run=root/'logs/reliability_reduced_v29_targeted_20261008/my_world_random_s3'
 rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
 truths=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
 start=next(r for r in rows if r.get('mission')=='LAND')
 initial=next(r for r in rows if r.get('mission')=='CAMERA_FWD')
 mav=CameraAirframe();w=mav.w;w.t=epoch=start['stamp']
 cond=json.loads((run/'run.json').read_text())['conditions'];w.cond=cond
 w.cam_sev={k:int(cond['camera'][k]) for k in CAMERA_KEYS}
 w.rng=random.Random(3);w.np_rng=np.random.default_rng(3)
 p=initial['pose']['data']['pose']['position'];mav.home_marker_xy=(p['x'],p['y'])
 q=start['pose']['data']['pose']['orientation']
 w.yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
 tt=np.array([float(r['t_sim']) for r in truths]);tx=np.array([[float(r[k]) for k in ('x','y','z')] for r in truths])
 w.p=np.array([np.interp(epoch,tt,tx[:,k]) for k in range(3)])
 samples=[]
 for r in rows:
  if epoch-.2<=r['stamp']<=epoch+125 and r.get('pose'):
   p=r['pose']['data']['pose']['position'];truth=np.array([np.interp(r['stamp'],tt,tx[:,k]) for k in range(3)])
   samples.append((r['stamp'],np.array([p[k] for k in ('x','y','z')])-truth))
 et=np.array([t for t,e in samples]);errors=np.array([e for t,e in samples])
 wind=cond['wind'];w.wind=WindDrift(mean=wind['speed'],gust=wind['gust'],period=wind['gust_period_s'],dir_rad=math.radians(wind['dir_deg']),turb=.5*wind['veer_deg']/20*wind['speed']/8,seed=3,dt=DT)
 for i in range(round(epoch/DT)):w.wind(i*DT)
 v=start['velocity']['data']['twist']['linear'];w.v=np.array([v[k] for k in ('x','y','z')]);w.v[:2]-=w.wind(epoch)
 w.speed_cap=5.;w.sp_pos=(*mav.pos(),w.yaw)
 leaf=PrecisionDescent(mav,marker_m=3.1,hfov_rad=.851919,**({'gain':gain} if gain is not None else {}));leaf.initialise()
 pending=deque();previous=None;changes=[];status=py_trees.common.Status.RUNNING
 for index in range(1,12501):
  e=np.array([np.interp(w.t,et,errors[:,k]) for k in range(3)]);w.gps_err=e[:2];w.baro_err=e[2];w.baro_noise=0.
  if index%5==0:
   eye=w.p+np.array([.16*math.cos(w.yaw),.16*math.sin(w.yaw),0.])
   if w.rng.random()>=cond['camera']['frame_drop']:pending.append((w.t+cond['camera']['latency_ms']/1000,w._qr(eye,math.pi/2)['off']))
  while pending and pending[0][0]<=w.t:mav.qr_offset=pending.popleft()[1]
  if index%20==0:
   status=leaf.update()
   reason=leaf.feedback_message.split(';')[0].split(' at ')[0].split(' ')[0]
   if reason!=previous:changes.append((round(w.t-epoch,2),leaf.feedback_message));previous=reason
   if status is not py_trees.common.Status.RUNNING:break
  w.t+=DT
  if recorded_pose:
   w.p=np.array([np.interp(w.t,tt,tx[:,k]) for k in range(3)])
  else:w._step_airframe()
 result=dict(seconds=w.t-epoch,status=str(status),precision=mav.landing_precision,changes=changes,position=mav.pos(),truth=w.p.tolist(),home_fix=mav.home_marker_xy,normal_response_s=.6,extra_queue_s=0.,limitation='recorded estimator error and initial pose; regenerated camera observations; no ROS arrival ordering')
 print(json.dumps(result));return result

def test_recorded_landing_leaves_time_for_normal_disarm():
 result=replay();(root/'logs/reliability_v29_landing_physics_baseline_20261008.json').write_text(json.dumps(result,indent=2))
 assert result['status']=='Status.SUCCESS'
 assert result['precision'].startswith('PRECISE')
 assert result['seconds']<=60.,'landing entry at 853.36 must leave normal LAND/disarm time before first_arm + 900'

if __name__=='__main__':
 replay(recorded_pose='--recorded-pose' in sys.argv)
