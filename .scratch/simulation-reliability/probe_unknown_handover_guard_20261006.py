"""AST-only calm handover proof, not a simulation or sensor qualification.

The fixture has a known prior position controller maintaining 0.3 m/s until
the first own zero-velocity packet arrives. There is no wind in this plant.
"""
import ast
from collections import deque
import json
import math
from pathlib import Path
from types import SimpleNamespace,MethodType
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
tree=ast.parse(path.read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
names=('_reset_drift','_heading_at','_effective_command','_compensated')
namespace=dict(np=np,math=math,deque=deque)
for name in names:
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
original_compensated=namespace['_compensated']
def wait_for_own_response(self,vx,vy):
    delay=float(self._g('vel_command_delay_s'))
    if self._model_t is not None and not any(sent+delay<=self._model_t+1e-9 for sent,_ in self._command_history):
        self._expect_world=self._fcu_velocity.copy()
        self._ground_world=self._fcu_velocity.copy()
        self._model_t=self._fcu_velocity_t
        self._drift_prev,self._drift_prev_t=self._pos,self._fcu_velocity_t
        return vx,vy
    return original_compensated(self,vx,vy)
namespace['_compensated']=wait_for_own_response
parameters=dict(vel_response_s=.6,vel_command_delay_s=.4,drift_filter_s=.05,drift_comp_gain=1.,max_drift_comp=1.5)
time=1.
node=SimpleNamespace(_pos=(0.,0.),_yaw=0.,_pose_t=1.,_pose_history=deque(),
    _fcu_velocity_t=1.,_fcu_velocity=np.array([.3,0.]),_g=lambda n:parameters[n],_now=lambda:time,
    _velocity_fresh=lambda:True)
for name in names:setattr(node,name,MethodType(namespace[name],node))
node._reset_drift()
node._expect_world=node._fcu_velocity.copy()
node._ground_world=node._fcu_velocity.copy()
node._model_t=1.
node._drift_prev,node._drift_prev_t=node._pos,1.
node._command_history.append((1.,np.zeros(2)))
node._sent_heading[1.]=0.
velocity=.3
rows=[]
for i in range(1,13):
    time=1.+i*.05
    if time>1.4+1e-9:velocity+=(0.-velocity)*(.05/.6)
    node._fcu_velocity_t=time;node._fcu_velocity=np.array([velocity,0.])
    node._pose_t=time;node._pos=(node._pos[0]+velocity*.05,0.)
    correction=node._compensated(0.,0.)
    rows.append(dict(stamp=time,own_command_has_arrived=time>=1.4,
        measured_velocity_mps=velocity,expected_velocity_mps=node._expect_world[0],
        inferred_disturbance_mps=node._wind_world[0],inferred_disturbance_rate_mps2=node._wind_rate_world[0],
        commanded_body_velocity_mps=correction[0]))
before=[r for r in rows if r['stamp']<1.4-1e-9]
print(json.dumps(dict(plant='known prior position control, zero wind, actual FCU sample timestamps',
    rows=rows,peak_false_prearrival_disturbance_mps=max(abs(r['inferred_disturbance_mps']) for r in before)),indent=2))
assert max(abs(r['inferred_disturbance_mps']) for r in before)<.03, 'Unobserved prior position target was implicitly treated as a zero actuator target'
