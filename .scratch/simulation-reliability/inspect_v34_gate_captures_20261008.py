import bisect,csv,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v34_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];rows=[r for r in rows if r.get('pose')]
truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()))
for t in [792.3,796,800,803.7,806,809,812.6,815,819,823]:
 r=min(rows,key=lambda r:abs(r['stamp']-t));n=min(truth,key=lambda n:abs(float(n['t_sim'])-t))
 print(json.dumps(dict(t=r['stamp'],pose=r['pose']['data']['pose'],velocity=r['velocity']['data']['twist']['linear'],truth={k:n[k] for k in ['x','y','z']},mission=r.get('mission'))))
print('lidar first',next((run/'onboard_lidar.jsonl').open())[:1800])
