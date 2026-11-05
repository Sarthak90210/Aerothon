"""Minimal certificate failure when a delay bound is treated as exact latency.
No ROS/controller instantiation, world geometry file, or flight parameter writes.
"""
import ast,hashlib,json,math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
root=Path(__file__).resolve().parents[2]
path=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
method=next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,ast.FunctionDef) and n.name=='motion_clear')
wall=1.1;seen=[]
def segment_clear(a,b):
    seen.append(list(b));return wall-max(a[1],b[1])>=.725
parameters=dict(vel_command_delay_s=.4,vel_response_s=.6,braking_accel_mps2=.5)
node=SimpleNamespace(_g=parameters.__getitem__,_now=lambda:0.,_pose_t=0.,_fcu_velocity_t=0.,
    _command_known=lambda t:True,
    _effective_command=lambda t:np.array([0.,.8]) if t<.1 else np.zeros(2),
    _planner=SimpleNamespace(segment_clear=segment_clear))
namespace=dict(self=node,np=np,math=math,ground=np.array([0.,.2]),wind=np.array([0.,-.15]),
    wind_rate=np.zeros(2),rotation=np.eye(2),receipt_turn=0.,budget=.2)
exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
accepted=namespace['motion_clear']((0.,.6))
# A faster .05 s channel is inside the declared .4 s delay bound. Zero true
# wind and the same .6 s first-order response; current ground velocity .2.
velocity=.2;position=0.;minimum=wall;dt=.01
for t in np.arange(0,6,dt):
    command=.6 if .05<=t<.65 else 0.
    velocity+=(command-velocity)*dt/.6;position+=velocity*dt
    minimum=min(minimum,wall-position)
report=dict(scope='Deterministic model counterexample, not a rendered qualification',
    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),certificate_accepted=bool(accepted),
    declared_delay_s=.4,actual_delay_s=.05,actual_response_s=.6,true_wind_mps=0.,
    model_disturbance_mps=-.15,initial_clearance_m=wall,
    predicted_minimum_clearance_m=wall-max(p[1] for p in seen),actual_minimum_clearance_m=minimum,
    parameters_written=False,actual_delay_within_declared_bound=True)
print(json.dumps(report,indent=2))
assert not accepted or minimum>=.7,'Point delay/observer assumption accepts a faster delivered unsafe pulse'
