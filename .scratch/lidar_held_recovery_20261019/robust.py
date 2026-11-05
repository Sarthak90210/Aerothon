import numpy as np
from load import *
new=load_module(); old=load_module(Path(__file__).with_name('old_lidar_odometry.py'),'old')
def run(mod,seq):
    e=mod.ScanOdometry(); s=''
    for c,t in seq:
        try: e.update(c,t); s+='T'
        except ValueError: s+='H'
    return s
res={'new':[], 'old':[]}
for seed in range(6):
    rng=np.random.default_rng(seed)
    for start in (0,40,80,95,105):
        seq=[]
        for c,t in zip(clouds[start:],stamps[start:]):
            r=np.linalg.norm(c,axis=1,keepdims=True); jitter=rng.normal(0,.005,(len(c),1)) if seed else 0
            seq.append((c*(1+jitter/np.maximum(r,1e-6)),t))
        for name,mod in (('new',new),('old',old)):
            s=run(mod,seq); tail=s.rfind('T'); longest=max(len(x) for x in s.split('T'))
            res[name].append((seed,start,s.count('T'),len(s),longest, s[-1]))
for name in res:
    r=res[name]; print(name,'runs',len(r),'ending held',sum(x[5]=='H' for x in r),'longest hold scans max',max(x[4] for x in r),'tracked frac min %.2f'%min(x[2]/x[3] for x in r))
