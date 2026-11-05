import math,collections
import numpy as np
from scipy.spatial import cKDTree
from load import *
m=load_module()
def icp(reference,current,initial=(0,0,0),iters=60):
    tree=cKDTree(reference)
    _,nb=tree.query(reference,k=7); local=reference[nb]; c=local-local.mean(axis=1,keepdims=True)
    vals,vecs=np.linalg.eigh(np.einsum('nki,nkj->nij',c,c)); normals=vecs[:,:,0]; line=vals[:,0]<.15*np.maximum(vals[:,1],1e-9)
    pose=np.array(initial,float); steps=[]
    for k in range(iters):
        rot=current@m.rotation(pose[2]).T; mv=rot+pose[:2]
        d,nn=tree.query(mv); valid=(d<.35)&line[nn]
        if valid.sum()<10: return dict(fail='nooverlap',k=k)
        p,n,q=rot[valid],normals[nn[valid]],reference[nn[valid]]
        err=np.einsum('ij,ij->i',n,mv[valid]-q); cut=max(.012,float(np.quantile(abs(err),.8))); keep=abs(err)<=cut
        p,n,err=p[keep],n[keep],err[keep]
        A=np.column_stack((n[:,0],n[:,1],-n[:,0]*p[:,1]+n[:,1]*p[:,0]))
        w=np.minimum(1.,.025/np.maximum(abs(err),1e-8))
        delta=np.linalg.lstsq(A*np.sqrt(w[:,None]),-err*np.sqrt(w),rcond=None)[0]
        pose+=delta; steps.append((np.linalg.norm(delta[:2]),abs(delta[2])))
        if steps[-1][0]<.0002 and steps[-1][1]<.0001: break
    mv=m.transform(current,pose); d,nn=tree.query(mv); use=(d<.15)&line[nn]
    res=np.einsum('ij,ij->i',normals[nn[use]],mv[use]-reference[nn[use]])
    return dict(pose=pose,iters=k+1,overlap0=float(valid.mean()),use=float(use.mean()),rmse=float(np.sqrt(np.mean(np.minimum(res**2,.15**2)))),lastdelta=steps[-1],line=float(line.mean()))
R=[icp(clouds[i-1],clouds[i]) for i in range(1,len(clouds))]
rm=np.array([r.get('rmse',np.nan) for r in R]); it=np.array([r.get('iters',0) for r in R])
print('pair rmse pct',np.nanpercentile(rm,[5,25,50,75,90,95,99]))
print('iters pct',np.percentile(it,[50,75,90,95,100]))
print('use pct',np.nanpercentile([r.get('use',np.nan) for r in R],[1,5,25,50]))
print('pose step pct (m)',np.nanpercentile([np.linalg.norm(r['pose'][:2]) for r in R if 'pose' in r],[50,90,99,100]))
print('yaw step pct (deg)',np.nanpercentile([abs(math.degrees(r['pose'][2])) for r in R if 'pose' in r],[50,90,99,100]))
# self-noise: rmse for scan vs itself shifted? compare scans 2 apart and 10 apart
for gap in (1,2,5,10,30):
    rr=[icp(clouds[i-gap],clouds[i]) for i in range(gap,len(clouds),3)]
    print('gap',gap,'rmse median',np.nanmedian([r.get('rmse',np.nan) for r in rr]),'>40mm frac',np.mean([r.get('rmse',1)>.04 for r in rr]))
# returns count over time
n=[len(c) for c in clouds]; print('returns per 20:',[int(np.mean(n[i:i+20])) for i in range(0,len(n),20)])
