"""Evaluate saved truth separately, then align prior onboard decisions for diagnosis."""
import bisect,hashlib,json,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from check_track import lanes,to_lane,rect_gap,load_track
batch=root/'logs/reliability_focused_paired_scan_navigation_verified_20261007'
run=batch/'my_world_field_s2'
layout=json.loads((run/'layout.json').read_text());track=load_track(str(run/'track.csv'))
gaps=[]
for row in track:
    if not row['armed'] or row['z']<=.3:continue
    measurements=[]
    for i,lane in enumerate(lanes(layout)):
        u,v=to_lane(row,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and row['z']<lane[5]:
            measurements.append((lane[4]/2-abs(v),f'lane_{i}_wall'))
    for i,obstacle in enumerate(layout.get('obstacles',[])):
        if row['z']<obstacle['h']+.3:
            hx,hy=layout.get('home_world',[0,0])
            measurements.append((rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],row['x'],row['y']),f'obstacle_{i}'))
    if measurements:
        gap,feature=min(measurements);gaps.append(dict(row=row,gap_m=gap,feature=feature))
source=batch/'my_world_field_s2_forecasts.json'
records=json.loads(source.read_text())['records'];times=[row['before']['clock_s'] for row in records]
minimum=min(gaps,key=lambda row:row['gap_m'])
first_loss=next(row for row in gaps if row['gap_m']<.725)
first_violation=next(row for row in gaps if row['gap_m']<.7)
def window(at):
    return records[max(0,bisect.bisect_left(times,at-1.)):bisect.bisect_right(times,at+.5)]
near=window(first_violation['row']['t'])
report=dict(scope='Independent grading only; simulator truth never supplied to controller',
    first_reserve_loss=first_loss,first_clearance_violation=first_violation,minimum=minimum,
    near_violation_records=near,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    near_violation_faults=dict(Counter(row['detail'].get('fault','none') for row in near)),
    near_violation_planner=dict(Counter(row['detail'].get('planner_state','none') for row in near)),
    controller_changed=False,causality_established=False)
target=batch/'field2_clearance_review.json'
with target.open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps(dict(first_reserve_loss=first_loss,first_clearance_violation=first_violation,
    minimum=minimum,faults=report['near_violation_faults'],planner=report['near_violation_planner'],
    records=len(near)),indent=2))
