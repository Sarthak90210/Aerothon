"""Compare model response at receipt and FCU sample times, postflight only.

Onboard records are sampled at 5 Hz. Heading is interpolated from that record,
so this measures a timestamp mismatch contribution, not an exact controller
replay or a causal proof that the complete rendered failure is fixed.
"""
import bisect
import json
import math
import sys
from pathlib import Path
import numpy as np

out=Path(sys.argv[1])
boards=[json.loads(line) for line in (out/'onboard.jsonl').open()]
boards=[r for r in boards if 'pose' in r]
nav=[r for r in boards if r.get('mission')=='RETURN_CORRIDOR']
bt=[r['stamp'] for r in boards]
yaw=[]
for r in boards:
    q=r['pose']['data']['pose']['orientation']
    yaw.append(math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)))
yaw=np.unwrap(yaw)
commands=[]
for line in (out/'flight_commands.jsonl').open():
    r=json.loads(line);d=r['data']
    if d.get('type_mask')==1479 and nav[0]['stamp']-2<=r['stamp']<=nav[-1]['stamp']:
        heading=float(np.interp(r['stamp']+.4,bt,yaw))
        c,s=math.cos(heading),math.sin(heading);v=d['velocity']
        commands.append((r['stamp']+.4,np.array([c*v['x']-s*v['y'],s*v['x']+c*v['y']])))
ct=[r[0] for r in commands]
sampled=[]
for r in nav:
    v=r['velocity']['data'];stamp=v['header']['stamp'];t=stamp['sec']+stamp['nanosec']*1e-9
    sampled.append((r['stamp'],t,np.array([v['twist']['linear'][k] for k in ('x','y')])))
start=sampled[0][1]
velocity=sampled[0][2].copy()
grid=np.arange(start,sampled[-1][0]+.003,.002)
pred=[]
for t in grid:
    i=bisect.bisect_right(ct,t)-1
    target=commands[i][1] if i>=0 else np.zeros(2)
    velocity+=(target-velocity)*(1-math.exp(-.002/.6))
    pred.append(velocity.copy())
pred=np.array(pred)
rows=[]
for now,stamp,actual in sampled:
    receipt=np.array([np.interp(now,grid,pred[:,i]) for i in range(2)])
    sample=np.array([np.interp(stamp,grid,pred[:,i]) for i in range(2)])
    rows.append(dict(stamp=now,measurement_stamp=stamp,measurement_age_s=now-stamp,
        actual=actual.tolist(),receipt_time_residual=(actual-receipt).tolist(),sample_time_residual=(actual-sample).tolist(),
        mismatch_contribution=(sample-receipt).tolist()))
summary=[]
for lo,hi in ((869.5,880.5),(880.5,884.5),(884.5,895.5)):
    selection=[r for r in rows if lo<=r['stamp']<=hi]
    def rms(key):return float(np.sqrt(np.mean(np.array([r[key] for r in selection])**2)))
    summary.append(dict(window=[lo,hi],samples=len(selection),receipt_residual_rms=rms('receipt_time_residual'),
        aligned_residual_rms=rms('sample_time_residual'),mismatch_rms=rms('mismatch_contribution'),
        mismatch_peak=float(max(np.linalg.norm(r['mismatch_contribution']) for r in selection))))
print(json.dumps(dict(summary=summary,window=[r for r in rows if 879.5<=r['stamp']<=881.5],
    limitation=__doc__),indent=2))
