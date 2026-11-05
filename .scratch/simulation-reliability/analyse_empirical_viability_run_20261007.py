"""Classify a completed empirical-reserve probe without hiding its timeout."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('capture',type=Path)
parser.add_argument('--out',type=Path,required=True)
args = parser.parse_args()
report = json.loads(args.capture.read_text())
root = Path(__file__).resolve().parents[2]
rows = report['rows']
minimum = report['minimum_actual_clearance_m']
last = rows[-1] if rows else None
first_unsafe = next((r for r in rows if r['independent_clearance_m']<.7),None)
if report['passed'] and minimum>=.7:
    status = 'TRAVERSAL_PASSED_PHYSICAL_FIXTURE_ONLY'
elif minimum is not None and minimum<.7:
    status = 'CLEARANCE_FAILURE'
elif last is not None and last['stamp']>=149.9:
    status = 'SAFE_DIAGNOSTIC_HORIZON_WITH_TRAVERSAL_FAILURE'
else:
    status = 'INCOMPLETE_OR_FAILED'
transitions = []
previous = None
for row in rows:
    detail = row['detail']
    mode = detail.get('diagnostic_mode')
    if mode!=previous:
        transitions.append(dict(stamp=row['stamp'],mode=mode,
            pose=row['pose'],
            actual_clearance_m=row['independent_clearance_m'],
            observed_clearance_m=detail['observed_clearance_m'],
            empirical_forecast_error_max_m=detail.get('diagnostic_error_max_m'),
            empirical_raw_residual_rate_max_mps2=detail.get('diagnostic_raw_residual_rate_max_mps2'),
            empirical_travel_reserve_m=detail.get('diagnostic_travel_reserve_m'),
            permitted_speed_mps=detail.get('diagnostic_travel_speed_mps')))
    previous = mode
result = dict(status=status,diagnostic_only=True,
    original_traversal_passed=report['passed'],original_failure=report['failure'],
    seed=report['seed'],kind=report['kind'],wind_profile=report['diagnostic_wind_profile'],
    actual_minimum_clearance_m=minimum,
    first_recorded_clearance_failure=None if first_unsafe is None else dict(
        stamp=first_unsafe['stamp'],clearance=first_unsafe['independent_clearance_m']),
    last_stamp=None if last is None else last['stamp'],records=len(rows),
    observed_forecast_error_max_m=report['diagnostic_error_max_m'],
    observed_raw_residual_rate_max_mps2=report['diagnostic_raw_residual_rate_max_mps2'],
    transitions=transitions,capture_sha256=hashlib.sha256(args.capture.read_bytes()).hexdigest(),
    analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    source_hashes=report['source_sha256'],
    current_source_hashes_match=all(hashlib.sha256((root/path).read_bytes()).hexdigest()==value
        for path,value in report['source_sha256'].items()))
assert not args.out.exists()
args.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('transitions','source_hashes','original_failure')}))
