"""Locate the measured failure without altering its grade or source evidence."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'sim'))
from check_track import lanes, to_lane, rect_gap

run = root / 'logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013'
layout = json.loads((run / 'layout.json').read_text())
track = json.loads((run / 'evaluation_track.json').read_text())
minimum = (float('inf'), None, None)
below = []
for row in track:
    if not row['armed'] or row['z'] <= .3:
        continue
    candidates = []
    for index, lane in enumerate(lanes(layout)):
        u, v = to_lane(row, layout, lane)
        if 0 <= u <= lane[3] and abs(v) <= lane[4] / 2 and row['z'] < lane[5]:
            candidates.append((lane[4] / 2 - abs(v), f'lane {index} wall'))
    for index, obstacle in enumerate(layout.get('obstacles', [])):
        if row['z'] < obstacle['h'] + .3:
            hx, hy = layout['home_world']
            poly = [(x - hx, y - hy) for x, y in obstacle['poly']]
            candidates.append((rect_gap(poly, row['x'], row['y']), f'obstacle {index}'))
    if candidates:
        value, feature = min(candidates)
        if value < minimum[0]:
            minimum = (value, feature, row)
        if value < .7:
            below.append(dict(stamp=row['t'], clearance_m=value, feature=feature))
grade = json.loads((run / 'grade.json').read_text())
assert abs(minimum[0] - grade['measured_corridor_clearance_m']) < 1e-12
report = dict(run=str(run), measured_minimum_m=minimum[0], required_m=.7,
              nearest_feature=minimum[1], native_aircraft_sample=minimum[2],
              below_floor_samples=len(below), below_floor=below,
              original_grade_modified=False, algorithm_modified=False)
path = Path(__file__).parent / 'final_field_clearance_review.json'
path.write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k != 'below_floor'}, indent=2))
