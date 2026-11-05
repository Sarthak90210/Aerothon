"""Scratch empirical reserve built into the connected path clearance.

Prediction errors and residual derivatives come only from completed onboard
observations. They are empirical diagnostics, not guaranteed future bounds.
The original full .70+.025 motion certificate remains untouched. The extra
reserve gates travel; it cannot prevent already-certified hold cancellation.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind',choices=('dirty','late'),required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--wind',choices=('default','calm'),default='default')
parser.add_argument('--out',required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
import math
import numpy as np
from collections import deque
standard_publish = case.node._publish
forecasts = deque()
error_max = 0.
rate_max = 0.
error_samples = 0
last_measurement = None
previous_wind = None
hold_target = None
hold_count = 0
ready_since = None
mode = 'BOOTSTRAP'
strict_path_world = []
strict_plan_t = None

def observe_forecast(self):
    global last_measurement,previous_wind,error_max,rate_max,error_samples
    stamp = self._pose_t
    if stamp is None or stamp==last_measurement:
        return None
    while forecasts and forecasts[0][0] <= stamp+1e-8:
        due,predicted = forecasts.popleft()
        if abs(due-stamp) <= .025:
            error_max = max(error_max,float(np.linalg.norm(np.array(self._pos)-predicted)))
            error_samples += 1
    if self._response_known and previous_wind is not None and last_measurement is not None:
        span = stamp-last_measurement
        if span>1e-8:
            rate_max = max(rate_max,float(np.linalg.norm((self._wind_world-previous_wind)/span)))
    previous_wind = self._wind_world.copy()
    last_measurement = stamp
    if not self._response_known:
        return None
    delay = float(self._g('vel_command_delay_s'))
    tau = float(self._g('vel_response_s'))
    actuator = self._ground_world-self._wind_world
    point = np.array(self._pos,dtype=float)
    points = [point.copy()]
    at = 0.
    while at<delay-1e-9:
        span = min(.05,delay-at)
        target = self._effective_command(self._now()+at)
        actuator += (target-actuator)*min(1.,span/tau)
        point += (actuator+self._wind_world+(at+span)*self._wind_rate_world)*span
        points.append(point.copy())
        at += span
    forecasts.append((stamp+delay,point.copy()))
    return points

def reserved_path(self):
    global strict_path_world,strict_plan_t
    base = self._planner
    horizon = float(self._g('vel_command_delay_s'))+float(self._g('vel_response_s'))
    minimum_speed = float(self._g('min_progress_m'))/float(self._g('progress_window_s'))
    planning_reserve = error_max+.5*rate_max*horizon*horizon+minimum_speed*horizon
    guard = type(base)(clearance=base.clearance+planning_reserve,
                       resolution=base.resolution,lookahead=base.lookahead,
                       occupied_radius=base.occupied_radius)
    for name in ('points','tree','bearings','ranges','sensor_origin'):
        setattr(guard,name,getattr(base,name))
    c,s = math.cos(self._yaw),math.sin(self._yaw)
    px,py = self._pos
    while len(strict_path_world)>1 and math.dist(self._pos,strict_path_world[0])<.2:
        strict_path_world.pop(0)
    body = [(c*(x-px)+s*(y-py),-s*(x-px)+c*(y-py)) for x,y in strict_path_world]
    if body and strict_plan_t is not None and self._now()-strict_plan_t<.5 and all(
            guard.segment_clear(a,b) for a,b in zip([(0,0)]+body,body)):
        return [(0,0)]+body
    axis = math.atan2(math.sin(self._axis-self._yaw),math.cos(self._axis-self._yaw))
    path = guard.plan(axis)
    strict_plan_t = self._now()
    strict_path_world = [(px+c*x-s*y,py+s*x+c*y) for x,y in path[1:]]
    return path

def empirical_publish(self,vx,vy,front,bearing,extra):
    global hold_target,hold_count,ready_since,mode
    if 'fault' in extra:
        standard_publish(vx,vy,front,bearing,extra)
        return
    # Advance the observer once to this measurement. The original publish
    # sees the same header and cannot advance it a second time.
    self._compensated(0.,0.)
    pending = observe_forecast(self)
    if hold_target is None and mode=='BOOTSTRAP':
        hold_target = np.array(self._pos,dtype=float)
        hold_count += 1
    delay = float(self._g('vel_command_delay_s'))
    horizon = delay+float(self._g('vel_response_s'))
    reserve = error_max+.5*rate_max*horizon*horizon
    path = reserved_path(self) if self._axis is not None else []
    speed = 0.
    minimum = None
    if len(path)>1:
        points = np.linspace(path[0],path[1],max(2,int(math.dist(path[0],path[1])/.05)+2))
        minimum = float(min(self._planner.distances(points)))
        speed = max(0.,min(self.cruise,(minimum-self._planner.clearance-.025-reserve)/horizon))
    queue_clear = False
    if pending is not None:
        c,s = math.cos(self._yaw),math.sin(self._yaw)
        origin = np.array(self._pos)
        body = [np.array([[c,s],[-s,c]])@(point-origin) for point in pending]
        queue_clear = all(self._planner.segment_clear(a,b) for a,b in zip(body,body[1:]))
        queue_clear = queue_clear and min(self._planner.distances(body))>=self._planner.clearance+.025+error_max
    sufficient = error_samples>=max(1,math.ceil(delay/.05))
    minimum_speed = float(self._g('min_progress_m'))/float(self._g('progress_window_s'))
    travel_viable = sufficient and queue_clear and speed>=minimum_speed and self.state!='STUCK'
    if not travel_viable:
        if hold_target is None:
            hold_target = np.array(self._pos,dtype=float)
            hold_count += 1
        ready_since = None
        mode = 'EMPIRICAL_HOLD'
    elif hold_target is not None:
        if ready_since is None:
            ready_since = self._now()
        if self._now()-ready_since>=horizon and float(np.linalg.norm(self._ground_world))<=minimum_speed:
            hold_target = None
            ready_since = None
            mode = 'TRAVEL'
    if hold_target is not None:
        correction = .8*(hold_target-np.array(self._pos))
        correction *= min(1.,.25/max(1e-9,float(np.linalg.norm(correction))))
        c,s = math.cos(self._yaw),math.sin(self._yaw)
        vx,vy = c*correction[0]+s*correction[1],-s*correction[0]+c*correction[1]
        bearing = 0.
        self._progress_ref,self._progress_t = self._pos,self._now()
    elif len(path)>1:
        bearing = math.atan2(path[1][1],path[1][0])
        vx,vy = speed*math.cos(bearing),speed*math.sin(bearing)
        cap = float(self._g('max_lateral'))
        vy = max(-cap,min(cap,vy))
    extra = dict(extra,diagnostic_control_policy='empirical forecast-error path reserve',
                 diagnostic_mode=mode,diagnostic_error_max_m=error_max,
                 diagnostic_error_samples=error_samples,diagnostic_raw_residual_rate_max_mps2=rate_max,
                 diagnostic_travel_reserve_m=reserve,diagnostic_travel_speed_mps=speed,
                 diagnostic_path_minimum_m=minimum,diagnostic_queue_clear=bool(queue_clear),
                 diagnostic_path_body_m=path,diagnostic_hold_count=hold_count,
                 diagnostic_hold_target_world_m=None if hold_target is None else hold_target.tolist(),
                 diagnostic_reserve_is_empirical=True)
    standard_publish(vx,vy,front,bearing,extra)
case.node._publish = MethodType(empirical_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source = source.replace(needle,hook+'\n'+needle)
source = source.replace('case._through(drift=stress.WindDrift(seed=args.seed), **options)',
                        'case._through(drift=fixture_drift, **options)')
source = source.replace('except AssertionError as e:', 'except Exception as e:')
source = source.replace('failure = str(e)', "failure = type(e).__name__+': '+str(e)")
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='empirical forecast-error path reserve',diagnostic_wind_profile=wind_profile,"+
    "diagnostic_error_max_m=error_max,diagnostic_raw_residual_rate_max_mps2=rate_max,"+
    "minimum_actual_clearance_m=None if not hasattr(case,'closest_detail') else min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),"+
    "probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','.4','--out',args.out]
source = source.replace('detail=case.node.last_detail))',
    "detail=case.node.last_detail))\n    if len(rows)%200==0:\n        print(json.dumps(dict(progress_stamp=case.node._now(),mode=mode,pose=case.node._pos,error_max=error_max,rate_max=rate_max)),flush=True)")
# The physics and corruption fixtures stay unchanged. Still air is a distinct
# existing supported fixture case, never substituted into default gust trials.
root = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
import test_corridor_stress as stress
fixture_drift = stress.WindDrift(seed=args.seed) if args.wind=='default' else None
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',
    wind_profile=args.wind,fixture_drift=fixture_drift,
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
