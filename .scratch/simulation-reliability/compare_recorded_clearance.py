"""Compare recorded perception with separate native grading, offline only."""
import bisect
import json
import math
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim'))
from check_track import lanes,to_lane,rect_gap

out=Path(sys.argv[1])
board=[json.loads(s) for s in (out/'onboard.jsonl').read_text().splitlines()]
truth=[json.loads(s) for s in (out/'evaluation_vehicle_truth.jsonl').read_text().splitlines()]
times=[r['stamp'] for r in truth]
layout=json.loads((out/'layout.json').read_text());hx,hy=layout.get('home_world',[0,0])
errors=[]
for r in board:
    d=r.get('avoidance') or {}
    observed=d.get('observed_clearance_m')
    if not (95<r['stamp']<118 and isinstance(observed,(int,float))):continue
    i=bisect.bisect_left(times,r['stamp'])
    candidates=[j for j in (i-1,i) if 0<=j<len(truth)]
    i=min(candidates,key=lambda j:abs(times[j]-r['stamp']))
    p=truth[i];row=dict(x=p['x']-hx,y=p['y']-hy,z=p['z'])
    distances=[]
    for lane in lanes(layout):
        u,v=to_lane(row,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and row['z']<lane[5]:
            distances.append(lane[4]/2-abs(v))
    for obstacle in layout['obstacles']:
        if row['z']<obstacle['h']+.3:
            distances.append(rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],row['x'],row['y']))
    if distances:errors.append(observed-min(distances))
report=dict(samples=len(errors),observed_minus_native_m=dict(
    median=float(np.median(errors)),p05=float(np.quantile(errors,.05)),
    p95=float(np.quantile(errors,.95)),maximum=float(max(errors)),minimum=float(min(errors))),
    source='recorded onboard diagnostics compared offline with independently stored native positions',
    limitation='nearest observation time; not a sensor calibration or proof of bounded uncertainty')
path=out/'clearance_comparison.json'
if path.exists():raise SystemExit('Output exists')
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
