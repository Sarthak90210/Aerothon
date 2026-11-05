"""Align recorded gate setpoints, estimates and independent truth postflight."""
import bisect,csv,hashlib,json,math
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=root/'logs/reliability_reduced_v28_targeted_20261008/my_world_random_s3'
rows=[json.loads(s) for s in (run/'onboard.jsonl').open()];truth=list(csv.DictReader((run/'evaluation_truth_track.csv').open()));commands=[json.loads(s) for s in (run/'flight_commands.jsonl').open()];commands=[c for c in commands if c['topic']=='/mavros/setpoint_position/local'];times=[c['stamp'] for c in commands]
counts=Counter(tuple(round(c['data']['pose']['position'][k],3) for k in ['x','y','z']) for c in commands if 749<c['stamp']<809)
records=[]
for t in range(749,809,4):
 r=min((r for r in rows if r.get('pose')),key=lambda r:abs(r['stamp']-t));n=min(truth,key=lambda n:abs(float(n['t_sim'])-r['stamp']));i=bisect.bisect_right(times,r['stamp'])-1;c=commands[max(0,i)];p=r['pose']['data']['pose']['position'];v=r['velocity']['data']['twist']['linear']
 records.append(dict(stamp=r['stamp'],estimated_xyz=p,actual_xyz={k:float(n[k]) for k in ['x','y','z']},velocity=v,command=c,avoidance=r.get('avoidance')))
report=dict(accepted=False,most_common_targets=counts.most_common(6),records=records,inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'onboard.jsonl',run/'evaluation_truth_track.csv',run/'flight_commands.jsonl',run/'run.json']})
(run/'gate_trace_diagnosis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
