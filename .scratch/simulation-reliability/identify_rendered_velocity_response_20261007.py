"""Postflight response identification; no parameter writes or controller imports."""
import bisect,json,math,sys
from pathlib import Path
import numpy as np
out=Path(sys.argv[1])
records=json.loads((out/'motion_forecasts.json').read_text())['records']
# The post-certificate detail contains the latest measured FCU velocity.
observed=[]
for r in records:
    t=r['before']['velocity_t'];v=r['detail'].get('ground_velocity_world_mps')
    if t is not None and v is not None and (not observed or t>observed[-1][0]+1e-8):
        observed.append((t,np.array(v)))
onboard=[json.loads(l) for l in (out/'onboard.jsonl').open()]
poses=[]
for r in onboard:
    if not r.get('pose'):continue
    data=r['pose']['data'];t=data['header']['stamp']['sec']+data['header']['stamp']['nanosec']*1e-9;q=data['pose']['orientation']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    if not poses or t>poses[-1][0]:poses.append((t,yaw))
pose_t=[p[0] for p in poses]
def heading(t):
    i=bisect.bisect_right(pose_t,t)
    if i==0:return poses[0][1]
    if i==len(poses):return poses[-1][1]
    a,b=poses[i-1],poses[i];f=(t-a[0])/(b[0]-a[0])
    return a[1]+f*math.atan2(math.sin(b[1]-a[1]),math.cos(b[1]-a[1]))
commands=[]
for l in (out/'flight_commands.jsonl').open():
    r=json.loads(l);d=r['data']
    if r['topic']=='/mavros/setpoint_raw/local' and d.get('type_mask')==1479:
        commands.append((r['stamp'],np.array([d['velocity']['x'],d['velocity']['y']])))
commands.sort(key=lambda p:p[0]);command_t=[p[0] for p in commands]
start=observed[0][0]+1.;stop=134.0
samples=[(a,b) for a,b in zip(observed,observed[1:]) if start<=a[0]<=stop and .01<=b[0]-a[0]<=.12]
mid=start+(stop-start)*.6
results=[]
for delay in np.arange(0,.601,.025):
    features=[];rates=[];times=[]
    for a,b in samples:
        t=(a[0]+b[0])/2;i=bisect.bisect_right(command_t,t-delay)-1
        if i<0:continue
        sent,body=commands[i];yaw=heading(sent+delay);co,si=math.cos(yaw),math.sin(yaw)
        command=np.array([co*body[0]-si*body[1],si*body[0]+co*body[1]])
        diff=command-(a[1]+b[1])/2
        features.append([[diff[0],1.,0.],[diff[1],0.,1.]])
        rates.append((b[1]-a[1])/(b[0]-a[0]));times.extend([t,t])
    x=np.array(features).reshape(-1,3);y=np.array(rates).reshape(-1);train=np.array(times)<mid
    coef=np.linalg.lstsq(x[train],y[train],rcond=None)[0]
    residual=y-x@coef
    results.append(dict(delay_s=float(delay),response_s=float(1./coef[0]) if coef[0]>0 else None,
        train_acceleration_rmse_mps2=float(np.sqrt(np.mean(residual[train]**2))),
        heldout_acceleration_rmse_mps2=float(np.sqrt(np.mean(residual[~train]**2))),
        constant_bias_acceleration_world_mps2=coef[1:].tolist(),samples=int(len(y)//2)))
report=dict(scope='Postflight empirical first-order model assessment; not a qualified physical envelope',
    controller_parameters_written=False,simulator_truth_input=False,
    nominal=dict(delay_s=.4,response_s=.6),training_interval=[start,mid],heldout_interval=[mid,stop],
    selected_by_training=min(results,key=lambda r:r['train_acceleration_rmse_mps2']),candidates=results,
    limitations=['FCU velocity derivatives amplify capture noise.',
        'A first-order response may omit FCU position stabilisation and acceleration limiting.',
        'Empirical fit cannot qualify future gust bounds or authorize an automatic parameter change.'])
with (out/'empirical_velocity_response_20261007.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='candidates'},indent=2))
