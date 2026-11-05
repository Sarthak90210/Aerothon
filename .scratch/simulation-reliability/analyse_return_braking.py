"""Offline FCU/command comparison. Simulator truth remains evaluation only."""
import json
import math
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares

out = Path(sys.argv[1])
rows = [json.loads(s) for s in (out/'onboard.jsonl').read_text().splitlines()]
last = 0
print('t x y yaw state clearance cmd-x cmd-y ground-x ground-y wind-x wind-y fcu-x fcu-y')
for a in rows:
    t = a['stamp']
    if not (98 < t < 107 and t-last > .25):
        continue
    last = t
    p = a['pose']['data']['pose']; q = p['orientation']
    yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    d = a['avoidance']; v = a['velocity']['data']['twist']['linear']
    values = [t,p['position']['x'],p['position']['y'],yaw,d.get('state'),
              d.get('observed_clearance_m'),d.get('cmd_vx'),d.get('cmd_vy_left'),
              *d.get('ground_velocity_world_mps',[]),*d.get('disturbance_world_mps',[]),v['x'],v['y']]
    print(' '.join(str(round(x,3)) if isinstance(x,(float,int)) else str(x) for x in values))

# Estimate command-to-FCU response using only onboard pose/velocity/setpoints.
# Fit before the clearance failure and report error; this is identification,
# not proof that a first-order model safely bounds the aircraft response.
selected = [r for r in rows if 98 < r['stamp'] < 106]
times = np.array([r['stamp'] for r in selected])
yaws = []
measured = []
for r in selected:
    q = r['pose']['data']['pose']['orientation']
    yaws.append(math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)))
    v = r['velocity']['data']['twist']['linear']
    measured.append([v['x'],v['y']])
yaws = np.unwrap(yaws); measured = np.array(measured)
commands = [json.loads(s) for s in (out/'flight_commands.jsonl').read_text().splitlines()]
commands = [r for r in commands if 97 < r['stamp'] < 106 and r['data'].get('type_mask') == 1479]
ct = np.array([r['stamp'] for r in commands])
cw = []
for r in commands:
    yaw = np.interp(r['stamp'],times,yaws)
    v = r['data']['velocity']; c,s = math.cos(yaw),math.sin(yaw)
    cw.append([c*v['x']-s*v['y'],s*v['x']+c*v['y']])
cw = np.array(cw)
grid = np.arange(times[0],times[-1]+.01,.01)
def response(parameters):
    tau, delay, wx, wy = parameters
    indices = np.clip(np.searchsorted(ct,grid-delay,side='right')-1,0,len(ct)-1)
    v = measured[0].copy(); predicted = []
    a = 1-math.exp(-.01/tau)
    for command in cw[indices]:
        v += (command+np.array([wx,wy])-v)*a
        predicted.append(v.copy())
    return np.column_stack([np.interp(times,grid,np.array(predicted)[:,i]) for i in range(2)])
fit = least_squares(lambda p:(response(p)-measured).ravel(),[.6,.1,0,0],
                    bounds=([.05,0,-1,-1],[3,.8,1,1]),diff_step=.01)
report = dict(first_order_tau_s=float(fit.x[0]),transport_delay_s=float(fit.x[1]),
              constant_residual_world_mps=fit.x[2:].tolist(),
              velocity_rmse_mps=float(np.sqrt(np.mean((response(fit.x)-measured)**2))),
              configured_tau_rmse_mps=float(np.sqrt(np.mean((response([.6,0,0,0])-measured)**2))),
              source='onboard FCU pose, velocity and actual recorded MAVROS commands only',
              limitation='fit of an approximate model; not a clearance or hardware qualification')
(out/'onboard_response_fit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
