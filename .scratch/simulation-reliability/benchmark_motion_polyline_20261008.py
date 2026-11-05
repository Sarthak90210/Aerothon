"""Measure equivalent per-segment and batched clearance certificates."""
import json,math,sys,time,statistics
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_avoidance/avoidance')]
from avoidance.local_planner import LocalPlanner
from test_local_planner import wall_scan
p=LocalPlanner();p.observe(*wall_scan())
t=np.linspace(0,1,105);points=np.column_stack((t,.15*np.sin(t*2)))
methods={'individual':lambda:all(p.segment_clear(a,b) for a,b in zip(points,points[1:])), 'batch':lambda:p.polyline_clear(points)}
results={}
for name,method in methods.items():
 spans=[]
 for _ in range(30):
  start=time.perf_counter();assert method();spans.append(time.perf_counter()-start)
 results[name]=dict(median_ms=1000*statistics.median(spans),maximum_ms=1000*max(spans),segments=104)
results['median_speedup']=results['individual']['median_ms']/results['batch']['median_ms']
(root/'logs/reliability_motion_polyline_benchmark_20261008.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
