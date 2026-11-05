"""Read camera results and flight observations around the closed search failure."""
import bisect,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_render_rb_rotated_s20261003_observation_repairs_20261007'
onboard=[json.loads(line) for line in (out/'onboard.jsonl').read_text().splitlines()]
stamps=[row['stamp'] for row in onboard]
events=[]
for line in (out/'detector_events.jsonl').read_text().splitlines():
    row=json.loads(line)
    if row['detector']!='red_timing' or not 197<=row['received_stamp']<=208:continue
    detail=row['detail']
    state=(detail.get('status'),detail.get('blobs'),len(detail.get('exclusions',[])))
    if not events or events[-1]['state']!=state:
        observed=onboard[max(0,bisect.bisect_right(stamps,row['received_stamp'])-1)]
        events.append(dict(received_stamp=row['received_stamp'],capture_stamp=detail.get('capture_stamp'),
            state=state,pose=observed.get('pose'),velocity=observed.get('velocity'),
            projected_exclusions=detail.get('exclusions'),observed_ground=detail.get('observed'),
            red_frac=detail.get('red_frac'),confirmed_area_m2=detail.get('confirmed_area_m2')))
report=dict(scope='Recorded onboard red timing; no simulator inputs',transitions=events)
with (out/'red_detector_timing_review_20261007.json').open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps([dict(received_stamp=row['received_stamp'],capture_stamp=row['capture_stamp'],state=row['state'],
    pose=row['pose']['data']['pose']['position'],confirmed_area_m2=row['confirmed_area_m2']) for row in events],indent=2))
