"""Read archived FCU callback cadence; this is not candidate qualification."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008'
times=[]
for line in (run/'onboard.jsonl').open():
    r=json.loads(line)
    v=r.get('velocity',{}).get('data',{})
    t=v.get('header',{}).get('stamp',{})
    if 'sec' in t:
        value=t['sec']+t.get('nanosec',0)*1e-9
        if not times or value>times[-1]:times.append(value)
gaps=sorted(b-a for a,b in zip(times,times[1:]))
out=dict(run=str(run.relative_to(root)),distinct_recorded_captures=len(times),median_recorder_gap_s=gaps[len(gaps)//2] if gaps else None,p95_recorder_gap_s=gaps[int(.95*(len(gaps)-1))] if gaps else None,limitation='onboard recorder aliases intermediate callbacks; not controller history or new-source qualification')
print(json.dumps(out))
