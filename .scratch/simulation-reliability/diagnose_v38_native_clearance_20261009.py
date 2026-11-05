"""Preserve actual failed native return input/output evidence, evaluation only."""
import bisect
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root / 'sim'), str(root / 'scripts')]
from check_track import lanes, to_lane, rect_gap

run = root / 'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
def read(name):
    rows = []
    for line in (run / name).read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows
layout = json.loads((run / 'layout.json').read_text())
onboard = read('onboard.jsonl')
times = [row['stamp'] for row in onboard]
home = layout.get('home_world', [0, 0])
gaps = []
for pose in read('evaluation_vehicle_truth.jsonl'):
    if not 395 <= pose['stamp'] <= 429.3:
        continue
    i = bisect.bisect_right(times, pose['stamp']) - 1
    if i < 0 or not onboard[i].get('flight', {}).get('data', {}).get('armed') or pose['z'] <= .3:
        continue
    point = dict(x=pose['x'] - home[0], y=pose['y'] - home[1], z=pose['z'])
    for j, lane in enumerate(lanes(layout)):
        u, v = to_lane(point, layout, lane)
        if 0 <= u <= lane[3] and abs(v) <= lane[4] / 2 and point['z'] < lane[5]:
            gaps.append((lane[4] / 2 - abs(v), pose, f'lane {j} wall', onboard[i]))
    for j, obstacle in enumerate(layout.get('obstacles', [])):
        if point['z'] < obstacle['h'] + .3:
            gaps.append((rect_gap([(x-home[0], y-home[1]) for x,y in obstacle['poly']], point['x'], point['y']), pose, f'obstacle {j}', onboard[i]))
minimum = min(gaps, key=lambda item: item[0])
near = [row for row in onboard if 395 <= row['stamp'] <= 429.3]
result = dict(minimum_clearance_m=minimum[0], independent_truth=minimum[1], surface=minimum[2],
    recorded_before=minimum[3], onboard_return=near,
    actual_flight_commands=[row for row in read('flight_commands.jsonl') if 395 <= row['stamp'] <= 429.3],
    actual_received_lidar=[row for row in read('onboard_lidar.jsonl') if 395 <= row['received_stamp'] <= 429.3],
    layout=layout, configuration=json.loads((run/'configuration.json').read_text()),
    diagnostic_only=True, accepted=False)
(run/'return_clearance_diagnosis.json').write_text(json.dumps(result, indent=2))
print(json.dumps(dict(minimum_clearance_m=minimum[0], independent_truth=minimum[1], surface=minimum[2],
    onboard_pose=minimum[3].get('pose'), avoidance=minimum[3].get('avoidance'),
    samples=len(near), commands=len(result['actual_flight_commands']), scans=len(result['actual_received_lidar']))))
