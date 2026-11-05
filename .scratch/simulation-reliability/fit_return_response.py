"""Compare response hypotheses using recorded FCU velocity and commands only."""
import json,math,sys
from pathlib import Path
import numpy as np
out=Path(sys.argv[1]);rows=[json.loads(v) for v in (out/'onboard.jsonl').open()]
r=[v for v in rows if 866<v['stamp']<877];tt=np.array([v['stamp'] for v in r]);yaws=[];vv=[]
for v in r:
    q=v['pose']['data']['pose']['orientation'];yaws.append(math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)));vel=v['velocity']['data']['twist']['linear'];vv.append([vel['x'],vel['y']])
yaws=np.unwrap(yaws);vv=np.array(vv)
cmd=[json.loads(v) for v in (out/'flight_commands.jsonl').open()];cmd=[v for v in cmd if 864<v['stamp']<877 and v['data'].get('type_mask')==1479]
ct=np.array([v['stamp'] for v in cmd]);cv=np.array([[v['data']['velocity']['x'],v['data']['velocity']['y']] for v in cmd]);grid=np.arange(tt[0],tt[-1]+.01,.02)
results=[]
for frame in ('yaw_when_sent','yaw_when_arrived'):
    best=None
    for delay in np.arange(.2,.601,.025):
        yaw=np.interp(ct+(delay if frame=='yaw_when_arrived' else 0),tt,yaws)
        cw=np.column_stack((np.cos(yaw)*cv[:,0]-np.sin(yaw)*cv[:,1],np.sin(yaw)*cv[:,0]+np.cos(yaw)*cv[:,1]))
        ix=np.clip(np.searchsorted(ct,grid-delay,side='right')-1,0,len(ct)-1)
        for tau in np.arange(.35,.851,.025):
            vel=vv[0].copy();pred=[]
            for target in cw[ix]:vel+=(target-vel)*(1-math.exp(-.02/tau));pred.append(vel.copy())
            pred=np.array(pred);sample=np.column_stack([np.interp(tt,grid,pred[:,i]) for i in range(2)]);residual=vv-sample;bias=residual.mean(axis=0);err=float(np.sqrt(np.mean((residual-bias)**2)))
            if best is None or err<best['rmse']:best=dict(frame=frame,tau=float(tau),delay=float(delay),rmse=err,residual_bias=bias.tolist())
    results.append(best)
print(json.dumps(dict(results=results,limitation='Approximate response fits only; no safety bound or hardware qualification',source='recorded onboard FCU velocity, pose and commanded body velocity'),indent=2))
