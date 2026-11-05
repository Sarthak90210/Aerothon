"""Compare independently graded loss with actual recorded controller detail."""
import bisect,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'scripts')]
from check_track import load_track,lanes,to_lane,rect_gap
out=root/'logs/reliability_reduced_v17_targeted_20261008/my_world_field_s1'
track=load_track(str(out/'evaluation_truth_track.csv'));layout=json.loads((out/'layout.json').read_text())
gaps=[];hx,hy=layout.get('home_world',[0,0])
for r in track:
    if not r['armed'] or r['z']<=.3:continue
    for lane in lanes(layout):
        u,v=to_lane(r,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:gaps.append((lane[4]/2-abs(v),r,'wall'))
    for i,obstacle in enumerate(layout.get('obstacles',[])):
        if r['z']<obstacle['h']+.3:gaps.append((rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],r['x'],r['y']),r,f'obstacle {i}'))
minimum=min(gaps,key=lambda item:item[0]);t=minimum[1]['t']
def read(path):return [json.loads(line) for line in path.read_text().splitlines()]
rows=read(out/'onboard.jsonl');times=[r['stamp'] for r in rows]
before=rows[bisect.bisect_right(times,t)-1]
near=[dict(stamp=r['stamp'],phase=r.get('mission'),avoidance=r.get('avoidance'),pose=r.get('pose',{}).get('data',{}).get('pose'),velocity=r.get('velocity',{}).get('data',{}).get('twist')) for r in rows if abs(r['stamp']-t)<=1.]
timing=[]
for version,parent in [('v16','reliability_reduced_v16_remaining_targeted_20261008'),('v17','reliability_reduced_v17_targeted_20261008')]:
    data=read(root/'logs'/parent/'my_world_field_s1/onboard.jsonl')
    active=[r for r in data if r.get('mission')=='RETURN_CORRIDOR' and 'motion_computation_elapsed_s' in r.get('avoidance',{})]
    details=[r['avoidance'] for r in active]
    timing.append(dict(version=version,recorded_controller_samples=len(details),deadline_overruns=sum(d['motion_computation_elapsed_s']>d['motion_computation_budget_s']+1e-9 for d in details),max_computation_s=max((d['motion_computation_elapsed_s'] for d in details),default=None),max_scan_age_s=max((d['scan_age_s'] for d in details if d.get('scan_age_s') is not None),default=None),min_observed_clearance_m=min((d['observed_clearance_m'] for d in details if d.get('observed_clearance_m') is not None),default=None)))
result=dict(hypotheses=['Parallel verification perturbs callback deadlines','Projected lidar and independent geometry differ','Wind-response estimate misses incoming lateral motion','Gate-to-corridor handover starts inside required clearance','Planner recovery is blocked by an unobserved sector'],minimum_clearance_m=minimum[0],time=t,surface=minimum[2],independent_sample=minimum[1],recorded_before=before,near=near,timing_comparison=timing,raw_receipt_and_snapshot_evidence_only=True)
(out/'return_clearance_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('near','recorded_before')}))
for r in near:print(json.dumps(dict(stamp=r['stamp'],phase=r['phase'],avoidance=r['avoidance'])))
