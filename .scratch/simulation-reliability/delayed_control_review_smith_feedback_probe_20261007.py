"""Scratch causal receipt predictor. Production and physical fixture are unchanged.

Every transmitted packet retains the production motion certificate and an
additional direct residual forecast. Historical residual rates are estimates,
not certified bounds on future disturbances. Fixture truth is evaluation only.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind', choices=('dirty', 'late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--out', required=True)
parser.add_argument('--wind', choices=('default', 'calm'), default='default')
parser.add_argument('--speed', type=float, default=.25)
parser.add_argument('--bootstrap', type=float, default=3.)
parser.add_argument('--rate-filter', type=float, default=.3)
parser.add_argument('--predict-position', action='store_true')
parser.add_argument('--fixed-heading', action='store_true')
parser.add_argument('--feedforward', type=float, default=.4)
parser.add_argument('--feedback', type=float, default=.8)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = r'''
import math
import numpy as np
ordinary_compensated = case.node._compensated
ordinary_publish = case.node._publish
residual_previous = None
residual_stamp = None
residual_rate = np.zeros(2)
bootstrap_target = None
diagnostic = {}

def measured_compensation(self,vx,vy):
    global residual_previous,residual_stamp,residual_rate
    ordinary_compensated(vx,vy)
    stamp = self._fcu_velocity_t
    if self._response_known and self._velocity_fresh():
        residual = self._ground_world-self._expect_world
        if stamp is not None and stamp!=residual_stamp:
            if residual_stamp is not None:
                span=stamp-residual_stamp
                if span>1e-8:
                    measured_rate=(residual-residual_previous)/span
                    residual_rate += (measured_rate-residual_rate)*min(1.,span/rate_filter)
            residual_previous=residual.copy()
            residual_stamp=stamp
        self._wind_world=residual.copy()
        # Keep the original capped derivative channel for the original
        # certificate. The direct forecast uses its separately recorded rate.
        self._wind_rate_world=residual_rate*min(1.,.8/max(1e-9,float(np.linalg.norm(residual_rate))))
        self._wind_innovation_world=np.zeros(2)
    c,s=math.cos(self._yaw or 0),math.sin(self._yaw or 0)
    rotation=np.array([[c,s],[-s,c]])
    horizon=float(self._g('vel_command_delay_s'))+float(self._g('vel_response_s'))
    disturbance=self._wind_world+feedforward*residual_rate
    disturbance*=min(1.,float(self._g('max_drift_comp'))/max(1e-9,float(np.linalg.norm(disturbance))))
    desired=np.array([vx,vy])
    output=desired-rotation@disturbance-feedback*(rotation@self._ground_world-desired)
    diagnostic.update(residual_world_mps=self._wind_world.tolist(),
                      causal_rate_world_mps2=residual_rate.tolist())
    return tuple(map(float,output))
case.node._compensated=MethodType(measured_compensation,case.node)

method=case.node._publish.__func__
code=textwrap.dedent(inspect.getsource(method))
start=code.index('        def motion_clear(command):')
end=code.index('        if not motion_clear((vx,vy)):')
old=code[start:end]
direct=old.replace('def motion_clear(command):','def motion_clear_direct(command):')
needle='                velocity += change'
assert direct.count(needle)==1
direct=direct.replace(needle,
    '                if t<delay+tau:\n                    change += dt*(rotation @ residual_rate)\n'+needle)
joined=old.replace('def motion_clear(command):','def motion_clear_original(command):')+direct
joined+='        def motion_clear(command):\n            return motion_clear_original(command) and motion_clear_direct(command)\n'
code=code[:start]+joined+code[end:]
namespace=dict(method.__globals__,residual_rate=residual_rate)
exec(compile(code,'<scratch retained original and direct residual certificate>','exec'),namespace)
qualified_publish=MethodType(namespace['_publish'],case.node)
if fixed_heading:
    case.node._yaw_rate_for=MethodType(lambda self,bearing:0.,case.node)

def receipt_forecast(self):
    delay=float(self._g('vel_command_delay_s'))
    tau=float(self._g('vel_response_s'))
    actuator=self._expect_world.copy()
    point=np.array(self._pos,dtype=float)
    at=0.
    while at<delay-1e-8:
        span=min(.05,delay-at)
        actuator+=(self._effective_command(self._now()+at)-actuator)*min(1.,span/tau)
        point+=(actuator+self._wind_world+at*residual_rate)*span
        at+=span
    return point

def smith_publish(self,vx,vy,front,bearing,extra):
    global bootstrap_target
    if 'fault' in extra:
        qualified_publish(vx,vy,front,bearing,extra)
        return
    self._compensated(0.,0.)
    if bootstrap_target is None:
        bootstrap_target=np.array(self._pos,dtype=float)
    c,s=math.cos(self._yaw or 0),math.sin(self._yaw or 0)
    rotation=np.array([[c,-s],[s,c]])
    forecast=receipt_forecast(self) if self._response_known else np.array(self._pos)
    target=bootstrap_target
    mode='bootstrap measured-position hold'
    if self._now()>=bootstrap and self._response_known and self.state!='STUCK':
        path=self._planner.path
        if len(path)>1:
            length=0.
            local=np.array(path[0],dtype=float)
            for a,b in zip(path,path[1:]):
                gap=math.dist(a,b)
                if length+gap>=.5:
                    local=np.array(a)+(np.array(b)-a)*(.5-length)/max(1e-9,gap)
                    break
                length+=gap
                local=np.array(b,dtype=float)
            target=np.array(self._pos)+rotation@local
            mode='causal receipt position tracking'
    error=target-(forecast if predict_position else np.array(self._pos))
    world=.65*error
    world*=min(1.,speed/max(1e-9,float(np.linalg.norm(world))))
    body=rotation.T@world
    vx,vy=map(float,body)
    if mode.startswith('bootstrap'):
        self._progress_ref,self._progress_t=self._pos,self._now()
    extra=dict(extra,diagnostic_policy='causal direct residual and receipt position control',
               diagnostic_mode=mode,diagnostic_receipt_position_world_m=forecast.tolist(),
               diagnostic_target_world_m=target.tolist(),diagnostic_observer=dict(diagnostic),
               diagnostic_assumptions='point forecasts only; no qualified future uncertainty bound')
    qualified_publish(vx,vy,front,bearing,extra)
case.node._publish=MethodType(smith_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source=source.replace(needle,hook+'\n'+needle)
source=source.replace('case._through(drift=stress.WindDrift(seed=args.seed), **options)',
                      'case._through(drift=fixture_drift, **options)')
source=source.replace('except AssertionError as e:', 'except Exception as e:')
source=source.replace('failure = str(e)', "failure = type(e).__name__+': '+str(e)")
source=source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='causal direct residual and receipt position control',"+
    "diagnostic_options=option_record,probe_template_sha256=template_hash,"+
    "minimum_actual_clearance_m=None if not hasattr(case,'closest_detail') else min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),seed=args.seed,")
sys.argv=[str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','.4','--out',args.out]
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
import test_corridor_stress as stress
fixture_drift=stress.WindDrift(seed=args.seed) if args.wind=='default' else None
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',fixture_drift=fixture_drift,
    speed=args.speed,bootstrap=args.bootstrap,rate_filter=args.rate_filter,
    feedforward=args.feedforward,feedback=args.feedback,
    predict_position=args.predict_position,fixed_heading=args.fixed_heading,
    option_record=vars(args),template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
