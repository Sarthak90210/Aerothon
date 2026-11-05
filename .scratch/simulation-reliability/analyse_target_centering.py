"""Read-only comparison of onboard QR rays and onboard capture-time poses."""
import bisect
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, 'src/aerothon_perception/perception_redzone')
from perception_redzone.georef import ground_point_q

root = Path(sys.argv[1])
poses = []
for line in (root/'onboard.jsonl').open():
    item = json.loads(line)
    if 'pose' not in item:
        continue
    data = item['pose']['data']
    header = data['header']['stamp']
    stamp = header['sec']+header['nanosec']*1e-9
    if not poses or stamp > poses[-1][0]:
        poses.append((stamp, data['pose']))
times = [p[0] for p in poses]
samples = []
for line in (root/'detector_events.jsonl').open():
    item = json.loads(line)
    if item.get('mission') != 'CENTER_TARGET' or item['detector'] != 'qr_timing':
        continue
    d = item['detail']
    if not d.get('matched') or d.get('offset', [0,0,0])[2] < .99:
        continue
    capture = d['capture_stamp']
    i = bisect.bisect_left(times, capture)
    candidates = [j for j in (i-1,i) if 0 <= j < len(times)]
    j = min(candidates, key=lambda k: abs(times[k]-capture))
    if abs(times[j]-capture) > .2:
        continue
    p = poses[j][1]
    pos,q = p['position'],p['orientation']
    quat = tuple(q[k] for k in ('w','x','y','z'))
    off = d['offset']
    ground = ground_point_q((off[0]+1)*640,(off[1]+1)*360,
                            (1280,720), .851919, pos['z'],
                            (pos['x'],pos['y']),quat,math.pi/2)
    yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']),
                     1-2*(q['y']**2+q['z']**2))
    naive = ground_point_q((off[0]+1)*640,(off[1]+1)*360,
                           (1280,720), .851919, pos['z'],
                           (pos['x'],pos['y']),
                           (math.cos(yaw/2),0,0,math.sin(yaw/2)),math.pi/2)
    samples.append(dict(capture=capture, ground=ground, yaw_only=naive,
                        aircraft=(pos['x'],pos['y']),offset=off))
def spread(key):
    xy=[s[key] for s in samples if s[key] is not None]
    mean=tuple(statistics.mean(p[k] for p in xy) for k in (0,1))
    distances=sorted(math.dist(p,mean) for p in xy)
    return dict(mean=mean,p95_radius_m=distances[int(.95*(len(distances)-1))],
                max_radius_m=max(distances))
print(json.dumps(dict(samples=len(samples),full_attitude=spread('ground'),
                     yaw_only=spread('yaw_only'),last=samples[-5:]),indent=2))
