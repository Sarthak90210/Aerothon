import math,sys,numpy as np
from load import *
m=load_module()
t0=stamps[0]; P=[r for r in rows if r['kind']=='pose']
ts=np.array([r['stamp'] for r in P]); xy=np.array([r['position'][:2] for r in P])
q=P[0]['orientation']; yaw0=math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2))
def fcu(t): return m.rotation(-yaw0)@(np.array([np.interp(t,ts,xy[:,0]),np.interp(t,ts,xy[:,1])])-np.array([np.interp(t0,ts,xy[:,0]),np.interp(t0,ts,xy[:,1])]))
e=m.ScanOdometry(); out={}
for i,(c,t) in enumerate(zip(clouds,stamps)):
    try: p,_=e.update(c,t); out[i]=p
    except ValueError: pass
step=int(sys.argv[1]) if len(sys.argv)>1 else 10
for i in range(0,len(clouds),step):
    if i in out: print(i,f'{stamps[i]-t0:5.1f}',np.round(out[i],2),'fcu',np.round(fcu(stamps[i]),2),'kf',)
