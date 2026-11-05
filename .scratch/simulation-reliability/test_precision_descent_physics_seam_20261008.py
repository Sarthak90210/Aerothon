"""Actual descent leaf, camera model and normal-response airframe, no ROS timers."""
import sys,math,random
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from test_headless_land_position_hold import world
from headless_world import Camera,Arena,DT,CAMERA_KEYS,WindDrift,W
from mission_bt.mission_tree import PrecisionDescent
import py_trees


class CameraAirframe:
    def __init__(self):
        self.w=world();w=self.w
        w.cond=W.conditions({'conditions':{'preset':'field'}},2)
        w.cam_sev={key:int(w.cond['camera'][key]) for key in CAMERA_KEYS}
        w.camera=Camera(.851919);w.rng=random.Random(2);w.np_rng=np.random.default_rng(2)
        w.arena=Arena(W.load(root/'sim/worlds/my_world.json'),'b')
        w.fcu=w.cond['fcu'];w.target_str=w.arena.start_payload
        w.glitch_gps=np.zeros(2);w.rejected_s=0.;w.coast_v=np.zeros(2);w.glitch_phase=0
        w.armed_at=None;w.t=0.;w.p=np.array([0.,0.,8.483935839901704]);w.gps_err=np.array([.2,-.1])
        w.v=np.zeros(3);w.sp_pos=(*w.est(),0.)
        wind=w.cond['wind']
        w.wind=WindDrift(mean=wind['speed'],gust=wind['gust'],period=wind['gust_period_s'],
            dir_rad=math.radians(wind['dir_deg']),turb=.5*wind['veer_deg']/20*wind['speed']/8,seed=2,dt=DT)
        # Reference established at the initial visual centre; no venue home
        # coordinates or marker truth enter any controller correction.
        marker=w.arena.markers[-1][0];a=w.arena.home_yaw
        self.home_marker_xy=(marker[0]-.16*math.cos(a)+.2,marker[1]-.16*math.sin(a)-.1)
        self.qr_offset=SimpleNamespace(x=0.,y=0.,z=0.);self.logs=[];self.landing_precision='UNKNOWN'
    def pos(self):return tuple(self.w.est())
    def alt(self):return self.pos()[2]
    def yaw(self):return self.w.yaw
    def home_local_xy(self):return (0.,0.)
    def qr_visible(self):return self.qr_offset.z>0
    def goto(self,x,y,z,yaw):self.w.sp_pos=(x,y,z,yaw)
    def log(self,*args,**kwargs):self.logs.append(args)
    def step(self,index):
        w=self.w;w.t+=DT;w._step_errors();w._step_airframe()
        if index%5==0:
            eye=w.p+np.array([.16*math.cos(w.yaw),.16*math.sin(w.yaw),0.])
            self.qr_offset=w._qr(eye,math.pi/2)['off']
            if w.rng.random()<w.cond['camera']['frame_drop']:
                self.qr_offset=SimpleNamespace(x=0.,y=0.,z=0.)


def test_normal_field_descent_achieves_visual_lock_instead_of_timeout():
    mav=CameraAirframe();leaf=PrecisionDescent(mav,marker_m=3.1,hfov_rad=.851919)
    leaf.initialise();status=py_trees.common.Status.RUNNING
    for index in range(1,12501):
        mav.step(index)
        if index%20==0:
            status=leaf.update()
            if status is not py_trees.common.Status.RUNNING:break
    print(dict(seconds=mav.w.t,status=str(status),precision=mav.landing_precision,position=mav.pos()))
    assert status is py_trees.common.Status.SUCCESS
    assert mav.landing_precision.startswith('PRECISE')
