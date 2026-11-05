"""Keep measured fault timeline distinct from proposed explanations."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for name in ['my_world_random_s3','my_world_random_s4']:
 run=root/'logs/reliability_reduced_v36_targeted_20261008'/name
 rows=[];previous=None;review=[]
 with (run/'onboard.jsonl').open() as f:
  for line in f:
   try:r=json.loads(line)
   except ValueError:continue
   a=r.get('avoidance') or {};key=(r.get('mission'),a.get('state'),a.get('fault'),a.get('altitude_motion_fault'))
   if key!=previous:
    review.append(dict(t=r['stamp'],mission=r.get('mission'),avoidance=a,result=r.get('result'),pose=r.get('pose'),velocity=r.get('velocity')));previous=key
   if r.get('velocity') and 675<=r['stamp']<=686:rows.append(dict(t=r['stamp'],pose_stamp=r.get('pose',{}).get('data',{}).get('header',{}).get('stamp'),velocity=r['velocity']['data']))
 (run/'motion_fault_diagnosis.json').write_text(json.dumps(dict(timeline=review,near_gate_failure_captures=rows,qualification=False),indent=2))
 for r in review:
  a=r['avoidance']
  if r['t']>660:print(json.dumps(dict(run=name,t=r['t'],mission=r['mission'],state=a.get('state'),fault=a.get('fault'),vertical_fault=a.get('altitude_motion_fault'),result=r.get('result'))))
