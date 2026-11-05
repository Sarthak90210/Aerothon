"""Causal zero-wind observer/certificate counterexample for faster native receipt."""
import argparse,ast,hashlib,json,math
from collections import deque
from pathlib import Path
from types import SimpleNamespace,MethodType
import numpy as np
root=Path(__file__).resolve().parents[2];path=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
parameters={}
for n in ast.walk(cls):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='p' and len(n.args)==2:
        try:parameters[ast.literal_eval(n.args[0])]=ast.literal_eval(n.args[1])
        except (ValueError,TypeError):pass
namespace=dict(np=np,math=math,deque=deque)
names=('_reset_drift','_heading_at','_command_known','_effective_command','_compensated')
for name in names:
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
parser=argparse.ArgumentParser()
parser.add_argument('--actual-delay',type=float,default=.05)
parser.add_argument('--model-delay',type=float)
parser.add_argument('--expect-rejection',action='store_true')
parser.add_argument('--no-favorable-disturbance',action='store_true')
args=parser.parse_args()
if args.model_delay is not None:parameters['vel_command_delay_s']=args.model_delay
time=1.
node=SimpleNamespace(_pos=(0.,0.),_yaw=0.,_pose_t=1.,_pose_history=deque(),
    _fcu_velocity_t=1.,_fcu_velocity=np.array([0.,.8]),_g=parameters.__getitem__,
    _now=lambda:time,_velocity_fresh=lambda:True)
for name in names:setattr(node,name,MethodType(namespace[name],node))
node._reset_drift();node._expect_world=np.array([0.,.8]);node._ground_world=np.array([0.,.8]);node._model_t=1.
node._drift_prev,node._drift_prev_t=node._pos,1.
node._command_history.extend([(0.,np.array([0.,.8])),(1.,np.zeros(2))]);node._sent_heading.update({0.:0.,1.:0.})
velocity=.8
for step in range(1,6):
    time=1.+step*.05
    target=0. if time-.025>=1.+args.actual_delay-1e-9 else .8
    velocity+=(target-velocity)*.05/.6
    node._fcu_velocity_t=node._pose_t=time;node._fcu_velocity=np.array([0.,velocity]);node._pos=(0.,node._pos[1]+velocity*.05)
    node._compensated(0.,0.)
wall=1.1;seen=[]
def clear(a,b):seen.append(list(b));return wall-max(a[1],b[1])>=.725
node._planner=SimpleNamespace(segment_clear=clear)
method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='motion_clear')
namespace.update(self=node,ground=node._ground_world.copy(),wind=node._wind_world.copy(),
    wind_rate=node._wind_rate_world.copy(),rotation=np.eye(2),receipt_turn=0.,budget=.2)
exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
accepted=namespace['motion_clear']((0.,.6))
if args.no_favorable_disturbance:
    # The diagnostic guard preserves the existing model check and also
    # evaluates the identical packet with zero inferred wind/rate.
    namespace['wind']=np.zeros(2);namespace['wind_rate']=np.zeros(2)
    accepted=accepted and namespace['motion_clear']((0.,.6))
position=0.;minimum=wall;dt=.01
for t in np.arange(0,6,dt):
    issued=[(0.,.8),(1.,0.),(time,.6),(time+.6,0.)]
    command=next(value for sent,value in reversed(issued) if sent<=time+t-args.actual_delay+1e-9)
    velocity+=(command-velocity)*dt/.6;position+=velocity*dt;minimum=min(minimum,wall-position)
report=dict(scope='Actual production observer and certificate AST; deterministic zero-wind physical fixture',
    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),assumed_delay_s=parameters['vel_command_delay_s'],
    actual_delay_s=args.actual_delay,actual_response_s=.6,true_wind_mps=0.,causally_inferred_false_wind_world=node._wind_world.tolist(),
    inferred_rate_world=node._wind_rate_world.tolist(),initial_ground_velocity_world=node._ground_world.tolist(),
    certificate_accepted=bool(accepted),predicted_minimum_clearance_m=wall-max(p[1] for p in seen),
    actual_minimum_clearance_m=minimum,parameters_written=False,no_favorable_disturbance_guard=args.no_favorable_disturbance)
print(json.dumps(report,indent=2))
assert not accepted or minimum>=.7,'Causal false disturbance from exact latency assumption admits unsafe motion'

if args.expect_rejection:assert not accepted,'Matched response must reject this unsafe pulse'
