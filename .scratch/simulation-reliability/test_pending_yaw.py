"""Check that turning cannot redirect a velocity pulse already in transit."""
import math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'sim'))
from rclpy.parameter import Parameter
from test_corridor_clearance_contract import controller
from test_local_planner import wall_scan


def test_pending_translation_is_certified_with_transmitted_yaw(controller):
    c,sent=controller;c.set_parameters([Parameter('vel_command_delay_s',value=.4)])
    c._planner.observe(*wall_scan(.73,1.75));c._ground_world=np.zeros(2);c._wind_world=np.zeros(2);c._wind_rate_world=np.zeros(2)
    c._compensated=lambda vx,vy:(vx,vy);c._command_history.append((.8,np.array([2.,0.])))
    c._publish(.8,0.,12.,1.,{});sp=sent[-1]
    velocity=np.zeros(2);point=np.zeros(2);dt=.005
    for t in np.arange(0.,7.,dt):
        if t<.2:goal=np.zeros(2)
        elif t<.4:
            yaw=sp.yaw_rate*.2;goal=2.*np.array([math.cos(yaw),math.sin(yaw)])
        elif t<1.:
            yaw=sp.yaw_rate*t;co,si=math.cos(yaw),math.sin(yaw)
            goal=np.array([co*sp.velocity.x-si*sp.velocity.y,si*sp.velocity.x+co*sp.velocity.y])
        else:goal=np.zeros(2)
        change=(goal-velocity)*dt/.6
        if t>=1.:change*=min(1.,.5*dt/max(1e-12,float(np.linalg.norm(change))))
        velocity+=change;point+=velocity*dt
        assert .73-point[1]>=.70,'yaw redirects an already transmitted velocity pulse toward the surface'
