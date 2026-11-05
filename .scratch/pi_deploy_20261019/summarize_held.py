"""Summarize a captured subscriber-only trace; --assert-tracking detects the live hold."""
import collections
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (HERE/'held_observation.jsonl').read_text().splitlines() if x.startswith('{')]
groups=collections.defaultdict(list)
for row in rows: groups[row['kind']].append(row)
scans=groups['scan']; statuses=groups['status']
stamps=np.array([s['stamp'] for s in scans]); received=np.array([s['received_s'] for s in scans])
returns=[sum(x is not None and max(.15,s['range_min'])<x<min(12.,s['range_max']) for x in s['ranges']) for s in scans]
pose=np.array([s['position'] for s in groups['pose']])
def percentiles(values):
    if not len(values): return None
    return dict(zip(['min','median','p95','max'],map(float,np.percentile(values,[0,50,95,100]))))
def euler(q):
    x,y,z,w=q
    return np.degrees([math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),
        math.asin(np.clip(2*(w*y-z*x),-1,1)),math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))])
angles=np.array([euler(s['orientation']) for s in groups['imu']])
out=dict(scan_count=len(scans),status_count=len(statuses),
    status_counts=dict(collections.Counter((s['state']+': '+s.get('reason','')) for s in statuses)),
    accepted_mapping_scans=len(groups['scan_slam']),
    scan_hz=float((len(scans)-1)/(received[-1]-received[0])),
    capture_interval_s=percentiles(np.diff(stamps)),receipt_interval_s=percentiles(np.diff(received)),
    scan_age_s=percentiles([s['ros_now_s']-s['stamp'] for s in scans]),
    valid_returns=percentiles(returns),scan_beams=sorted({len(s['ranges']) for s in scans}),
    scan_frames=sorted({s['frame'] for s in scans}),
    pose_span_m=(pose.max(axis=0)-pose.min(axis=0)).tolist() if len(pose) else None,
    imu_roll_deg=percentiles(angles[:,0]),imu_pitch_deg=percentiles(angles[:,1]),
    flight_state_counts=dict(collections.Counter(f"armed={s['armed']},mode={s['mode']}" for s in groups['state'])),
    static_transforms=[t for s in groups['tf_static'] for t in s['transforms']],
    maps=len(groups['map']))
(HERE/'held_summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='static_transforms'},indent=2))
if '--assert-tracking' in sys.argv:
    assert len(scans)>100 and out['scan_hz']>8, 'Capture did not contain a fresh scan stream'
    assert any(s['state']=='Tracking' for s in statuses), 'Fresh LiDAR, but all mapping statuses are Held'
