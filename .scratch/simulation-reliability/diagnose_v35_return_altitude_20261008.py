import csv,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v35_targeted_20261008/my_world_random_s4'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];rows=[r for r in rows if r.get('pose')]
truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
summary=[]
for t in range(642,695,3):
 r=min(rows,key=lambda r:abs(r['stamp']-t));n=min(truth,key=lambda n:abs(float(n['t_sim'])-t))
 summary.append(dict(t=r['stamp'],phase=r.get('mission'),estimated=r['pose']['data']['pose']['position'],truth={k:float(n[k]) for k in ['x','y','z']},velocity=r['velocity']['data']['twist']['linear'],avoidance=r.get('avoidance'),banner=r.get('banner_detail')))
(run/'return_altitude_diagnosis.json').write_text(json.dumps(summary,indent=2))
for r in summary:
 a=r['avoidance'] or {}
 print(json.dumps(dict(t=r['t'],phase=r['phase'],estimated_z=r['estimated']['z'],truth_z=r['truth']['z'],vz=r['velocity']['z'],hold=a.get('hold_alt_m'),cmd=a.get('cmd_vz'),avoid_state=a.get('state'))))
print('observed fields',list(rows[-1]))
