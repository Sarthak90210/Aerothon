"""Actual headless LAND service and physics must retain estimated XY control."""
import sys,threading
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'));sys.path.insert(0,str(root/'scripts'))
from headless_world import HeadlessWorld,DT

def world():
    w=HeadlessWorld.__new__(HeadlessWorld);w.lock=threading.Lock()
    w.mode='GUIDED';w.armed=True;w.t=1.;w.yaw=0.
    w.p=np.array([3.,-2.,4.]);w.v=np.zeros(3)
    w.gps_err=np.array([.2,-.1]);w.glitch=np.zeros(2);w.baro_err=w.baro_noise=0.
    w.wind=lambda t:(.15,0.)
    w.args=SimpleNamespace(vel_response_s=.6,vel_command_delay_s=0.)
    w.sp_pos=(0.,0.,4.,None);w.sp_vel=w.takeoff_alt=None;w.pending_velocity=deque()
    w.speed_cap=3.;w.arena=SimpleNamespace(contact=lambda x,y,z:None);w.contacts=[]
    w.fence_poly=None;w.params={};w.landed_t=None;w._event=lambda message:None
    return w

def test_real_land_mode_physics_holds_xy_against_retained_wind():
    w=world();initial=w.p.copy();w._srv_land(SimpleNamespace(),SimpleNamespace())
    for _ in range(3000):
        w.t+=DT;w._step_airframe()
        if not w.armed:break
    assert not w.armed and w.p[2]<=.02
    assert np.linalg.norm(w.p[:2]-initial[:2])<.4
    assert np.linalg.norm(w.p[:2])>3.,'LAND must not know the true home or reset aircraft position'
    assert w.args.vel_response_s==.6 and w.args.vel_command_delay_s==0.
