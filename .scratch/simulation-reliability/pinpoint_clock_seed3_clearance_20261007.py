"""Separate truth grading aligned with recorded onboard data, never flight input."""
import bisect,json,math,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from check_track import lanes,to_lane,rect_gap,load_track
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'logs/reliability_focused_clock_navigation_20261007/my_world_calm_s3'
assert out.resolve().is_relative_to((root/'logs').resolve())
layout=json.loads((out/'layout.json').read_text());track=load_track(str(out/'track.csv'))
gaps=[]
for r in track:
    if not r['armed'] or r['z']<=.3:continue
    measurements=[]
    for i,lane in enumerate(lanes(layout)):
        u,v=to_lane(r,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:
            measurements.append((lane[4]/2-abs(v),f'lane_{i}_wall'))
    for i,o in enumerate(layout.get('obstacles',[])):
        if r['z']<o['h']+.3:
            hx,hy=layout.get('home_world',[0,0])
            measurements.append((rect_gap([(x-hx,y-hy) for x,y in o['poly']],r['x'],r['y']),f'obstacle_{i}'))
    if measurements:
        gap,feature=min(measurements);gaps.append(dict(row=r,gap_m=gap,feature=feature))
first=next(g for g in gaps if g['gap_m']<.7);minimum=min(gaps,key=lambda g:g['gap_m'])
rows=[json.loads(line) for line in (out/'onboard.jsonl').open()];times=[r['stamp'] for r in rows]
def onboard(at):
    r=rows[max(0,bisect.bisect_right(times,at)-1)]
    return {k:r.get(k) for k in ('stamp','mission','pose','velocity','avoidance')}
window=[onboard(r['stamp']) for r in rows if first['row']['t']-1.<=r['stamp']<=first['row']['t']+.5]
timing=json.loads((out/'independent_command_receipt_timing.json').read_text())
packets=[r for r in timing if first['row']['t']-1.<=r['callback_sim_s']<=first['row']['t']+.5]
report=dict(scope='Independent geometry grading; recorder alignment is approximate, no stored full stopping prediction',
    first_violation=first,minimum=minimum,onboard_at_first=onboard(first['row']['t']),
    onboard_before_first=window,actual_callback_packets=packets,
    source_archive='logs/reliability_live_clock_navigation_candidate_fixed_20261007/frozen_source.zip')
target=out/'clearance_review_20261007.json'
with target.open('x') as h:json.dump(report,h,indent=2)
print(json.dumps(dict(first=first,minimum=minimum,stage=report['onboard_at_first']['mission'],
    detail=report['onboard_at_first']['avoidance'],packets=len(packets)),indent=2))
