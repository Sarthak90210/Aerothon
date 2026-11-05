"""Postflight attribution only. Independent truth never enters flight decisions."""
import bisect
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'sim'))
from check_track import lanes, to_lane, rect_gap

out = Path(sys.argv[1])
boards = [json.loads(line) for line in (out/'onboard.jsonl').open()]
boards = [row for row in boards if row.get('mission') == 'RETURN_CORRIDOR']
layout = json.loads((out/'layout.json').read_text())
hx, hy = layout['home_world']
native = []
for line in (out/'evaluation_vehicle_truth.jsonl').open():
    row = json.loads(line)
    if not boards[0]['stamp'] <= row['stamp'] <= boards[-1]['stamp']:
        continue
    point = dict(x=row['x']-hx, y=row['y']-hy, z=row['z'])
    distances = []
    for lane in lanes(layout):
        u, v = to_lane(point, layout, lane)
        if 0 <= u <= lane[3] and abs(v) <= lane[4]/2 and row['z'] < lane[5]:
            distances.append(lane[4]/2-abs(v))
    for obstacle in layout.get('obstacles', []):
        if row['z'] < obstacle['h']+.3:
            distances.append(rect_gap([(x-hx, y-hy) for x, y in obstacle['poly']], point['x'], point['y']))
    if distances:
        native.append(dict(stamp=row['stamp'], xy=[point['x'], point['y']], clearance=min(distances)))
times = [row['stamp'] for row in native]
violation = next((row for row in native if row['clearance'] < .7), None)
minimum = min(native, key=lambda row: row['clearance'])
center = (violation or minimum)['stamp']
result = dict(scope='Postflight evaluation only', first_violation=violation, minimum=minimum,
              return_interval=[boards[0]['stamp'], boards[-1]['stamp']], window=[], recovery=[])
last = -1
state = None
for row in boards:
    detail = row['avoidance']
    if detail.get('state') != state:
        state = detail.get('state')
        result['recovery'].append(dict(stamp=row['stamp'], detail=detail))
    if not center-3 <= row['stamp'] <= center+3 or row['stamp']-last < .2:
        continue
    last = row['stamp']
    index = min(bisect.bisect_left(times, row['stamp']), len(native)-1)
    result['window'].append(dict(stamp=row['stamp'], native=native[index], detail=detail))
target = out/'split_return_attribution_20261007.json'
assert not target.exists(), target
target.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
