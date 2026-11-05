"""Evaluate motion displacement without confusing GPS offset with model error."""
import bisect
import csv
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[2]
batch = root/'logs/reliability_combined_observation_focused_navigation_20261007'
results = []
for name in ('my_world_field_s4', 'my_world_field_s5'):
    run = batch/name
    prior = json.loads((run/'combined_clearance_review_20261007.json').read_text())
    with (run/'evaluation_truth_track.csv').open() as stream:
        track = [dict(t=float(r['t_sim']), x=float(r['x']), y=float(r['y'])) for r in csv.DictReader(stream)]
    times = [r['t'] for r in track]
    def point(t):
        i = bisect.bisect_right(times, t)
        if i <= 0 or i >= len(track):
            return None
        a, b = track[i-1], track[i]
        f = (t-a['t'])/(b['t']-a['t'])
        return [a['x']+f*(b['x']-a['x']), a['y']+f*(b['y']-a['y'])]
    forecasts = json.loads((batch/(name+'_forecasts.json')).read_text())['records']
    first = prior['first_violation']['stamp']
    comparisons = []
    biases = []
    nearby = [r for r in forecasts if first-2 <= r['before']['clock_s'] <= first+1]
    for record in nearby:
        before = record['before']
        c, s = math.cos(before['yaw']), math.sin(before['yaw'])
        command = [record['detail']['cmd_vx'], record['detail']['cmd_vy_left']]
        selected = [p for p in record['predictions'] if p['clear'] is True and math.dist(command, p['command']) < .008]
        for prediction in selected[-1:]:
            anchor = point(prediction['sample_epoch'])
            if anchor is None:
                continue
            biases.append(math.dist(anchor, before['pose']))
            for t, x, y in prediction['points_body']:
                endpoint = t+.05
                if endpoint > prediction['packet_wait']+1e-8:
                    continue
                actual = point(prediction['sample_epoch']+endpoint)
                if actual is None:
                    continue
                predicted_delta = [c*x-s*y, s*x+c*y]
                actual_delta = [actual[0]-anchor[0], actual[1]-anchor[1]]
                comparisons.append(dict(at=before['clock_s'], interval_s=endpoint,
                    relative_error_m=math.dist(predicted_delta, actual_delta),
                    predicted_displacement_m=predicted_delta, actual_displacement_m=actual_delta))
    report = dict(run=name, scope='Independent evaluation of queued-command displacement, truth never supplied to drone',
        prior_absolute_coordinate_error_is_not_a_motion_model_error=True,
        maximum_onboard_pose_offset_m=max(biases), comparisons=comparisons,
        maximum_relative_prefix_error_m=max(r['relative_error_m'] for r in comparisons),
        recorded_truth_interval_s=.1, interpolation_used_only_for_evaluation=True,
        first_clearance_violation_s=first)
    with (run/'relative_forecast_review_20261007.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    summary = {k:v for k,v in report.items() if k!='comparisons'}
    results.append(summary)
    print(json.dumps(summary), flush=True)
with (batch/'relative_forecast_review_20261007.json').open('x') as stream:
    json.dump(results, stream, indent=2)
