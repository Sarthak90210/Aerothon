"""Nominal inverse-response check using the production compensation AST."""
import ast,json,math
from collections import deque
from pathlib import Path
from types import SimpleNamespace,MethodType
import numpy as np
root=Path(__file__).resolve().parents[2]
path=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
src=path.read_text();tree=ast.parse(src);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
parameters={}
for n in ast.walk(cls):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='p' and len(n.args)==2:
  try:parameters[ast.literal_eval(n.args[0])]=ast.literal_eval(n.args[1])
  except (ValueError,TypeError):pass
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_compensated')
before=ast.unparse(method)
needle="prediction = float(self._g('vel_response_s'))"
assert before.count(needle)==1
after=before.replace(needle,"prediction = float(self._g('vel_response_s')) + float(self._g('vel_command_delay_s'))")
rows=[]
for delay in (0.,.4):
 for name,code in [('original',before),('queue_preview_candidate',after)]:
  namespace=dict(np=np,math=math);exec(compile(code,'<actual compensation AST>', 'exec'),namespace)
  parameters['vel_command_delay_s']=delay
  node=SimpleNamespace(_pos=(0.,0.),_yaw=0.,_fcu_velocity_t=1.,_pose_t=1.,_now=lambda:1.,_g=parameters.__getitem__,_velocity_fresh=lambda:True,_model_t=1.,_command_known=lambda stamp:True,_ground_world=np.zeros(2),_fcu_velocity=np.zeros(2),_expect_world=np.zeros(2),_drift_prev=(0.,0.),_drift_prev_t=1.,_wind_world=np.array([0.,.2]),_wind_rate_world=np.array([0.,.4]),_wind_innovation_world=np.zeros(2))
  command=MethodType(namespace['_compensated'],node)(0.,0.)[1]
  wind_at_receipt=.2+delay*.4
  # At zero ground speed, actuator velocity is -wind. Its first-order
  # response plus a linear wind derivative must have zero acceleration.
  ground_acceleration=(command+wind_at_receipt)/.6+.4
  rows.append(dict(model=name,delay_s=delay,command_mps=command,ground_acceleration_at_receipt_mps2=ground_acceleration))
print(json.dumps(dict(scope='Nominal declared first-order plant and exactly linear disturbance; no future wind bound or mission qualification',rows=rows),indent=2))
assert abs(rows[0]['command_mps']-rows[1]['command_mps'])<1e-12
assert abs(rows[2]['ground_acceleration_at_receipt_mps2'])>.2
assert abs(rows[3]['ground_acceleration_at_receipt_mps2'])<1e-12
