"""Inspect onboard certificate-to-publication timing, without simulator inputs."""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[2]
batch = root/'logs/reliability_lidar_fault_continuity_navigation_20261007'
summaries = []
for name in ('my_world_field_s4', 'my_world_field_s5', 'my_world_calm_s5'):
    path = batch/(name+'_forecasts.json')
    if not path.exists():
        continue
    records = json.loads(path.read_text())['records']
    checked = []
    for row in records:
        command = [row['detail']['cmd_vx'], row['detail']['cmd_vy_left']]
        accepted = [p for p in row['predictions'] if p['clear'] and math.dist(command, p['command']) < .008]
        if accepted:
            selected = accepted[-1]
            checked.append(dict(before=row['before']['clock_s'], publication=row['after_clock_s'],
                computation_age_s=row['after_clock_s']-selected['forecast_now'],
                capture_age_s=selected['forecast_now']-selected['sample_epoch'],
                ground_speed_mps=math.hypot(*row['before']['ground_world']),
                state=row['detail']['state'], command=command, detail=row['detail']))
    ages = sorted(r['computation_age_s'] for r in checked)
    summary = dict(run=name, checked=len(checked), maximum_certificate_to_publication_s=max(ages, default=None),
        p95_s=ages[min(len(ages)-1, int(.95*len(ages)))] if ages else None,
        worst_records=sorted(checked,key=lambda r:r['computation_age_s'],reverse=True)[:5],
        stale_computation_over_50ms=sum(age>.05 for age in ages),
        scope='Recorded onboard computation timing only; no claim of causal flight repair')
    summaries.append(summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='worst_records'}), flush=True)
with (batch/'certificate_publication_age_review_20261007.json').open('x') as stream:
    json.dump(summaries, stream, indent=2)
