"""Post-flight comparison over command delay, using exact recorded commands."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser()
p.add_argument('capture', type=Path)
p.add_argument('--out', type=Path, required=True)
args = p.parse_args()
report = json.loads(args.capture.read_text())
rows = report['rows']
evaluations = []
for i,row in enumerate(rows[:-8]):
    future = rows[i+8]
    assert abs(future['stamp']-row['stamp']-.4) < 1e-7
    attempts = row['certificate_attempts']
    sent = row['exact_body_command']
    selected = next((a for a in reversed(attempts)
                     if a['passed'] and np.linalg.norm(np.array(a['command'])-sent)<1e-7), None)
    if selected is None:
        continue
    prediction = next((q for q in selected['path'] if abs(q[0]-.4)<1e-7), None)
    if prediction is None:
        continue
    c,s = math.cos(row['measured_yaw']),math.sin(row['measured_yaw'])
    delta = np.array(future['pose'])-np.array(row['pose'])
    actual = np.array([[c,s],[-s,c]]) @ delta
    evaluations.append(dict(
        stamp=row['stamp'], pose=row['pose'],
        first_delay_interval_clearance_m=min(r['independent_clearance_m'] for r in rows[i:i+9]),
        exact_body_command=sent, observed_ground_world=row['observed_ground_world'],
        wind_rate_world=row['wind_rate_world'],
        predicted_body_displacement_m=prediction[1:3],
        actual_body_displacement_m=actual.tolist(),
        prediction_error_body_m=(actual-np.array(prediction[1:3])).tolist(),
        prediction_error_m=float(np.linalg.norm(actual-np.array(prediction[1:3])))))
evaluations.sort(key=lambda r:r['prediction_error_m'],reverse=True)
first = next((r for r in rows if r['independent_clearance_m']<.7), None)
summary = dict(
    capture_sha256=hashlib.sha256(args.capture.read_bytes()).hexdigest(),
    controller_sha256=report['source_sha256']['src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'],
    analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    recording_did_not_change_commands=report['diagnostic_policy']=='unchanged certificate recording',
    complete_delay_interval_comparisons=len(evaluations),
    first_recorded_clearance_breach=None if first is None else dict(stamp=first['stamp'],clearance=first['independent_clearance_m']),
    worst_delay_prediction_errors=evaluations[:8],
    accepted_commands_with_breach_inside_unavoidable_delay=[r for r in evaluations if r['first_delay_interval_clearance_m']<.7])
assert not args.out.exists()
args.out.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(comparisons=len(evaluations),
                     worst_error_m=max((r['prediction_error_m'] for r in evaluations),default=0),
                     first_breach=summary['first_recorded_clearance_breach'],
                     accepts_before_breach=len(summary['accepted_commands_with_breach_inside_unavoidable_delay']))))
