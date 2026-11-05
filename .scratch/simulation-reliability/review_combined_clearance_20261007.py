"""Align independent grading with onboard forecasts; never imported by flight."""
import bisect
import hashlib
import json
import math
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'sim'))
from check_track import lanes, to_lane, rect_gap, load_track

batch = root / 'logs/reliability_combined_observation_focused_navigation_20261007'
summaries = []
for name in ('my_world_field_s4', 'my_world_field_s5', 'my_world_calm_s5'):
    out = batch / name
    layout = json.loads((out / 'layout.json').read_text())
    track = load_track(str(out / 'track.csv'))
    forecasts = json.loads((batch / (name + '_forecasts.json')).read_text())['records']
    stamps = [r['t'] for r in track]
    def gap(row):
        values = []
        if not row['armed'] or row['z'] <= .3:
            return math.inf, None
        for i, lane in enumerate(lanes(layout)):
            u, v = to_lane(row, layout, lane)
            if 0 <= u <= lane[3] and abs(v) <= lane[4]/2 and row['z'] < lane[5]:
                values.append((lane[4]/2-abs(v), f'lane_{i}_wall'))
        hx, hy = layout.get('home_world', [0, 0])
        for i, obstacle in enumerate(layout.get('obstacles', [])):
            if row['z'] < obstacle['h']+.3:
                values.append((rect_gap([(x-hx, y-hy) for x, y in obstacle['poly']], row['x'], row['y']), f'obstacle_{i}'))
        return min(values) if values else (math.inf, None)
    graded = [dict(stamp=r['t'], gap_m=gap(r)[0], feature=gap(r)[1], pose=[r['x'], r['y']]) for r in track]
    first = next((r for r in graded if r['gap_m'] < .7), None)
    minimum = min(graded, key=lambda r: r['gap_m'])
    window = [r for r in forecasts if first and first['stamp']-2 <= r['before']['clock_s'] <= first['stamp']+1]
    comparisons = []
    for record in window:
        before = record['before']
        c, s = math.cos(before['yaw']), math.sin(before['yaw'])
        command = [record['detail']['cmd_vx'], record['detail']['cmd_vy_left']]
        accepted = [p for p in record['predictions'] if p['clear'] is True and math.dist(p['command'], command) < .008]
        for prediction in accepted[-1:]:
            for t, x, y in prediction['points_body']:
                end = t+.05
                if end > prediction['packet_wait']+1e-8:
                    continue
                stamp = prediction['sample_epoch']+end
                i = bisect.bisect_left(stamps, stamp)
                if i >= len(track) or abs(stamps[i]-stamp) > .12:
                    continue
                projected = [before['pose'][0]+c*x-s*y, before['pose'][1]+s*x+c*y]
                observed = [track[i]['x'], track[i]['y']]
                comparisons.append(dict(at=before['clock_s'], interval=end, error_m=math.dist(projected, observed), actual_clearance_m=gap(track[i])[0]))
    compact = [dict(before=r['before'], detail=r['detail'], forecasts=[dict(command=p['command'], clear=p['clear'], endpoint=p['points_body'][-1] if p['points_body'] else None) for p in r['predictions']]) for r in window]
    review = dict(scope='Independent evaluation only; no geometry supplied to controller', first_violation=first, minimum=minimum, nearby_onboard_forecasts=compact,
                  maximum_queued_prefix_error_m=max((r['error_m'] for r in comparisons), default=None), comparisons=comparisons,
                  recording_sha256=hashlib.sha256((out/'track.csv').read_bytes()).hexdigest())
    target = out / 'combined_clearance_review_20261007.json'
    with target.open('x') as stream:
        json.dump(review, stream, indent=2)
    summary = dict(run=name, first_violation=first, minimum=minimum, maximum_queued_prefix_error_m=review['maximum_queued_prefix_error_m'], window_records=len(window))
    summaries.append(summary)
    print(json.dumps(summary), flush=True)
with (batch/'combined_clearance_review_20261007.json').open('x') as stream:
    json.dump(summaries, stream, indent=2)
