"""Scratch corrected plant forecast with an explicitly queued terminal hold.

This replaces the known incorrect dynamic equation only in this process.
Geometry, sensors, aircraft physics and independent clearance grades remain
unchanged. Historical completed prediction error is empirical evidence and
cannot bound future Gaussian wind draws.
"""
import argparse
import ast
import hashlib
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--kind',choices=('dirty','late'),required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--out',required=True)
parser.add_argument('--speed',type=float,default=.15)
parser.add_argument('--wind',choices=('default','calm'),default='default')
parser.add_argument('--frozen-error-m',type=float)
args=parser.parse_args()
base=Path(__file__).with_name('delayed_control_review_smith_probe_20261007.py')
tree=ast.parse(base.read_text())
hook=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
          and any(isinstance(t,ast.Name) and t.id=='hook' for t in n.targets))
start=hook.index('method=case.node._publish.__func__')
end=hook.index('if fixed_heading:')
replacement=r'''
from collections import deque
completed_forecasts=deque()
empirical_error_max=0.
error_samples=0
certificate_comparisons=[]
viable_hold_anchor=None
method=case.node._publish.__func__
code=textwrap.dedent(inspect.getsource(method))
start=code.index('        def motion_clear(command):')
end=code.index('        if not motion_clear((vx,vy)):')
old=code[start:end].replace('def motion_clear(command):','def motion_clear_original(command):')
corrected = """        def motion_clear(command):
            global viable_hold_anchor
            actuator=rotation @ self._expect_world
            point=np.zeros(2)
            drift=ground-actuator
            derivative=rotation @ residual_rate
            step=.05
            horizon=delay+tau
            pending=[]
            candidate_rotation=np.array([[math.cos(receipt_turn),-math.sin(receipt_turn)],
                                         [math.sin(receipt_turn),math.cos(receipt_turn)]])
            pending.append((delay,candidate_rotation@np.array(command)))
            active=rotation @ self._effective_command(self._now())
            cutoff=delay+6*tau+float(np.linalg.norm(ground))/braking
            error=empirical_error_max if frozen_error is None else frozen_error
            forecast_points=[]
            for t in np.arange(0.,max(.1,cutoff),step):
                # Prior packets cannot be cancelled before their receipt.
                if t<delay-1e-9:
                    active=rotation @ self._effective_command(self._now()+t)
                while pending and pending[0][0]<=t+1e-9:
                    active=pending.pop(0)[1]
                current_drift=drift+min(t,horizon)*derivative
                # The actual fallback policy issues a position-hold packet
                # at every future control tick. It travels through the same
                # delay and actuator lag; it never sets ground velocity zero.
                if t>=step-1e-9:
                    forecast_actuator=actuator.copy()
                    receipt_point=point.copy()
                    future_active=active.copy()
                    future_pending=list(pending)
                    at=t
                    while at<t+delay-1e-9:
                        while future_pending and future_pending[0][0]<=at+1e-9:
                            future_active=future_pending.pop(0)[1]
                        forecast_actuator+=(future_active-forecast_actuator)*min(1.,step/tau)
                        receipt_point+=(forecast_actuator+drift+min(at,horizon)*derivative)*step
                        at+=step
                    desired=-.65*receipt_point
                    desired*=min(1.,speed/max(1e-9,float(np.linalg.norm(desired))))
                    forecast_rate=derivative if t<horizon else np.zeros(2)
                    correction=current_drift+(delay+tau)*forecast_rate
                    cap=float(self._g('max_drift_comp'))
                    correction*=min(1.,cap/max(1e-9,float(np.linalg.norm(correction))))
                    pending.append((t+delay,desired-correction))
                actuator+=(active-actuator)*min(1.,step/tau)
                next_drift=drift+min(t,horizon)*derivative
                velocity=actuator+next_drift
                nxt=point+velocity*step
                known=self._planner.known(np.linspace(point,nxt,2)).all()
                clearance=float(min(self._planner.distances(np.linspace(point,nxt,2))))
                if not self._planner.segment_clear(point,nxt) or not known or clearance<self._planner.clearance+.025+error:
                    certificate_comparisons.append(dict(stamp=self._now(),command=list(map(float,command)),
                        corrected=False,legacy=motion_clear_original(command),failure_at=float(t+step),
                        empirical_error_m=error))
                    return False
                forecast_points.append((t+step,nxt.copy()))
                point=nxt
            certificate_comparisons.append(dict(stamp=self._now(),command=list(map(float,command)),
                corrected=True,legacy=motion_clear_original(command),empirical_error_m=error))
            viable_hold_anchor=np.array(self._pos,dtype=float)
            return True
"""
# The surrounding production scope supplies the declared response, delay and
# braking assumptions. The corrected function itself separates actuator and
# additive residual motion and predicts a queued terminal position hold.
corrected=corrected.replace('            actuator=rotation @ self._expect_world',
    "            tau=float(self._g('vel_response_s'))\n            braking=float(self._g('braking_accel_mps2'))\n            actuator=rotation @ self._expect_world")
code=code[:start]+old+corrected+code[end:]
namespace=dict(method.__globals__,residual_rate=residual_rate,speed=speed,
    empirical_error_max=empirical_error_max,frozen_error=frozen_error,
    certificate_comparisons=certificate_comparisons,viable_hold_anchor=viable_hold_anchor)
exec(compile(code,'<corrected scratch actuator and queued terminal hold forecast>','exec'),namespace)
qualified_publish=MethodType(namespace['_publish'],case.node)
'''
hook=hook[:start]+replacement+hook[end:]
old='    self._compensated(0.,0.)\n    if bootstrap_target is None:'
new='''    global empirical_error_max,error_samples
    self._compensated(0.,0.)
    stamp=self._pose_t
    while completed_forecasts and completed_forecasts[0][0]<=stamp+1e-8:
        due,forecast=completed_forecasts.popleft()
        if abs(due-stamp)<.026:
            empirical_error_max=max(empirical_error_max,float(np.linalg.norm(np.array(self._pos)-forecast)))
            error_samples+=1
    namespace['empirical_error_max']=empirical_error_max
    if bootstrap_target is None:'''
assert hook.count(old)==1
hook=hook.replace(old,new)
old='    target=bootstrap_target\n    mode='
new="    target=bootstrap_target if self._now()<bootstrap or namespace['viable_hold_anchor'] is None else namespace['viable_hold_anchor']\n    completed_forecasts.append((stamp+float(self._g('vel_command_delay_s')),forecast.copy()))\n    mode="
assert hook.count(old)==1
hook=hook.replace(old,new)
template=Path(__file__).with_name('probe_gust_margin.py')
source=template.read_text()
needle='rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source=source.replace(needle,hook+'\n'+needle)
source=source.replace('case._through(drift=stress.WindDrift(seed=args.seed), **options)',
    'case._through(drift=fixture_drift, **options)')
source=source.replace('except AssertionError as e:', 'except Exception as e:')
source=source.replace('failure = str(e)',"failure = type(e).__name__+': '+str(e)")
source=source.replace('detail=case.node.last_detail))',
    "detail=case.node.last_detail,exact_body_command=[case.sent[-1].velocity.x,case.sent[-1].velocity.y]))\n    if len(rows)%200==0:\n        print(json.dumps(dict(stamp=case.node._now(),pose=case.node._pos,error_max=empirical_error_max)),flush=True)")
source=source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='corrected plant and delayed terminal hold forecast',diagnostic_options=option_record,"+
    "diagnostic_empirical_error_max_m=empirical_error_max,diagnostic_error_samples=error_samples,certificate_comparisons=certificate_comparisons,"+
    "base_helper_sha256=base_hash,probe_template_sha256=template_hash,"+
    "minimum_actual_clearance_m=None if not hasattr(case,'closest_detail') else min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),seed=args.seed,")
sys.argv=[str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','.4','--out',args.out]
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
import test_corridor_stress as stress
fixture_drift=stress.WindDrift(seed=args.seed) if args.wind=='default' else None
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',fixture_drift=fixture_drift,
    speed=args.speed,bootstrap=3.,rate_filter=.3,predict_position=True,fixed_heading=True,
    frozen_error=args.frozen_error_m,option_record=vars(args),
    base_hash=hashlib.sha256(base.read_bytes()).hexdigest(),
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
