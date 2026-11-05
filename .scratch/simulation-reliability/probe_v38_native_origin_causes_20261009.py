"""Private mathematical certificate controls on the retained actual scan."""
import json
import math
import sys
import inspect
import textwrap
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src/aerothon_avoidance/avoidance'))
from avoidance.local_planner import LocalPlanner
from avoidance.fast_connected_planner_candidate import FastConnectedPlanner
import avoidance.fast_connected_planner_candidate as fast_module

data=json.loads((root/'.scratch/simulation-reliability/v38_native_origin_20261009.json').read_text())
def observed_planner():
    planner=FastConnectedPlanner(occupied_radius=.4)
    planner.observe(data['bearings'],data['ranges'],sensor_origin=data['sensor_origin'],hits=data['hits'])
    return planner
def refine_certificate(self,xy):
    xy=np.asarray(xy,dtype=float).reshape(-1,2)
    if not np.isfinite(xy).all() or not self.known(xy).all():return False
    distances=self.distances(xy)
    if (distances<self.clearance).any():return False
    a,b=xy[:-1],xy[1:]
    da,db=distances[:-1],distances[1:]
    for _ in range(10):
        length=np.linalg.norm(b-a,axis=1)
        certified=(da+db-length)/2>=self.clearance
        if certified.all():return True
        a,b,da,db=a[~certified],b[~certified],da[~certified],db[~certified]
        mid=(a+b)/2
        if not self.known(mid).all():return False
        dm=self.distances(mid)
        if (dm<self.clearance).any():return False
        a,b=np.concatenate((a,mid)),np.concatenate((mid,b))
        da,db=np.concatenate((da,dm)),np.concatenate((dm,db))
    return False
def adaptive_segment(self,a,b):
    xy=np.linspace(a,b,max(2,int(math.dist(a,b)/.05)+2))
    return refine_certificate(self,xy)
def adaptive_polyline(self,points):
    points=np.asarray(points,dtype=float).reshape(-1,2)
    if len(points)<2 or not np.isfinite(points).all():return False
    xy=np.concatenate([np.linspace(a,b,max(2,int(math.dist(a,b)/.05)+2)) for a,b in zip(points,points[1:])])
    return refine_certificate(self,xy)

original_segment=LocalPlanner.segment_clear
original_polyline=LocalPlanner.polyline_clear
original_plan=FastConnectedPlanner.plan
plan_source=textwrap.dedent(inspect.getsource(original_plan))
needle="        if not len(qualified):\n"
assert plan_source.count(needle)==1
fallback='''        if not len(qualified):
            preserved=np.minimum.accumulate(raw_clearance[k:])[1:]-.025
            for index in range(len(endpoints)-1,-1,-1):
                if observed[index] and nearest[index]>=preserved[index] and self.segment_clear(raw[k],raw[k+1+index]):
                    qualified=np.array([index])
                    break
'''
namespace=dict(fast_module.__dict__)
exec(compile(plan_source.replace(needle,fallback+needle,1),'<private_compiled_shortcut_control>','exec'),namespace)
adaptive_plan=namespace['plan']
results=[]
for label in ['original','only_degenerate_origin','adaptive_continuous_clearance','adaptive_with_compiled_shortcut_fallback']:
    LocalPlanner.segment_clear=original_segment
    LocalPlanner.polyline_clear=original_polyline
    FastConnectedPlanner.plan=original_plan
    if label=='only_degenerate_origin':
        def origin_only(self,a,b):
            if math.dist(a,b)==0:
                return bool(self.known([a]).all() and self.distances([a])[0]>=self.clearance)
            return original_segment(self,a,b)
        LocalPlanner.segment_clear=origin_only
    elif label.startswith('adaptive'):
        LocalPlanner.segment_clear=adaptive_segment
        LocalPlanner.polyline_clear=adaptive_polyline
        if label=='adaptive_with_compiled_shortcut_fallback':
            FastConnectedPlanner.plan=adaptive_plan
    planner=observed_planner()
    path=planner.plan(0)
    dense=np.concatenate([np.linspace(a,b,1001) for a,b in zip(path,path[1:])]) if path else np.array([[0,0]])
    result=dict(control=label,path_found=bool(path),reason=planner.reason,
                observed_origin_m=float(planner.distances([(0,0)])[0]),
                dense_path_clearance_m=float(planner.distances(dense).min()),path=path)
    results.append(result)
LocalPlanner.segment_clear=original_segment
LocalPlanner.polyline_clear=original_polyline
FastConnectedPlanner.plan=original_plan
(root/'logs/reliability_v38_native_compiled_origin_causes_20261009.json').write_text(json.dumps(results,indent=2))
for result in results:print(json.dumps(result))
