"""Measure retained transit, preserving its original failed acceptance."""
import csv,hashlib,json,math,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v22_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()]
phase=[];previous=None
for r in rows:
    if r.get('mission') and r['mission']!=previous:
        phase.append([r['stamp'],r['mission']]);previous=r['mission']
start=next(t for t,p in phase if p=='RETURN_TRANSIT')
end=next(t for t,p in phase if t>start and p=='CAMERA_BANNER')
track=[r for r in csv.DictReader((run/'evaluation_truth_track.csv').open()) if start<=float(r['t_sim'])<=end]
length=sum(math.hypot(float(b['x'])-float(a['x']),float(b['y'])-float(a['y'])) for a,b in zip(track,track[1:]))
vel=[];caps=[]
for r in rows:
    if not start<=r.get('stamp',0)<=end:continue
    v=r.get('velocity',{}).get('data',{}).get('twist',{}).get('linear')
    if v:vel.append(math.hypot(v['x'],v['y']))
    cap=r.get('search_timing',{}).get('speed_cap_mps')
    if cap is not None:caps.append(cap)
review=dict(accepted_source=False,transit_start=start,transit_end=end,duration_sim_s=end-start,
    independent_horizontal_path_m=length,mean_path_speed_mps=length/(end-start),
    recorded_velocity_median_mps=statistics.median(vel),retained_search_caps_mps=sorted(set(caps)),
    source_seam='Normal built sequence has no acknowledged speed restoration between search and the high return transit',
    actual_sequence_red='logs/reliability_return_speed_lease_red_20261008.log',
    focused_green='logs/reliability_v23_navigation_speed_focused_20261008.log',
    prediction='Releasing the search lease after high-altitude/nadir prerequisites shortens transit without changing routes, sensors or actuators',
    actual_grade=json.loads((run/'navigation_grade.json').read_text()),
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'evaluation_truth_track.csv',run/'onboard.jsonl',run/'configuration.json',run/'source_manifest.json']})
(run/'return_speed_lease_diagnosis.json').write_text(json.dumps(review,indent=2))
print(json.dumps({k:review[k] for k in ['duration_sim_s','independent_horizontal_path_m','mean_path_speed_mps','recorded_velocity_median_mps','retained_search_caps_mps']}))
