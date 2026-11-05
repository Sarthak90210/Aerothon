"""Read preserved onboard decisions only; never supplied to flight software."""
from collections import Counter
import hashlib,json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_focused_paired_scan_navigation_verified_20261007'
source=out/'my_world_calm_s3_forecasts.json'
records=json.loads(source.read_text())['records']
return_records=[row for row in records if row['before']['clock_s']>=800.]
def reduced(row):
    return dict(before=row['before'],detail=row['detail'],
        prediction_attempts=len(row['predictions']),
        certified_predictions=sum(item['clear'] is True for item in row['predictions']))
first_margin=next((row for row in return_records if row['detail'].get('observed_clearance_m',10)<.725),None)
first_terminal=next((row for row in return_records if row['detail']['state']=='STUCK'),None)
last_before=next((row for row in reversed(return_records) if first_margin and
    row['before']['clock_s']<first_margin['before']['clock_s'] and row['predictions']),None)
faults=Counter(row['detail'].get('fault','none') for row in return_records)
reasons=Counter(row['detail'].get('planner_state','none') for row in return_records)
report=dict(scope='Onboard capture/command diagnosis; independent grade remains separate',
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),return_records=len(return_records),
    faults=dict(faults),planner_reasons=dict(reasons),
    maximum_reported_disturbance_mps=max((sum(value*value for value in row['before']['wind_world'])**.5
        for row in return_records),default=None),
    first_sampling_reserve_loss=reduced(first_margin) if first_margin else None,
    last_prediction_before_loss=reduced(last_before) if last_before else None,
    first_exhausted_recovery=reduced(first_terminal) if first_terminal else None,
    causality_established=False,controller_changed=False)
target=out/'seed3_return_observation_review.json'
with target.open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps(dict(records=report['return_records'],faults=report['faults'],
    reasons=report['planner_reasons'],maximum_reported_disturbance_mps=report['maximum_reported_disturbance_mps'],
    first_margin_stamp=first_margin['before']['clock_s'] if first_margin else None,
    first_stuck_stamp=first_terminal['before']['clock_s'] if first_terminal else None)))
