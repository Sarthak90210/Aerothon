"""Separate simulator evaluation of the closed flight's first red-margin loss."""
import bisect,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from check_track import red_polygons,rect_gap
out=root/'logs/reliability_render_rb_rotated_s20261003_observation_repairs_20261007'
layout=json.loads((out/'layout.json').read_text())
track=json.loads((out/'evaluation_track.json').read_text())
polys=red_polygons(layout)
measured=[]
for row in track:
    if row['armed'] and row['z']>.3:
        gap,name=min((rect_gap(poly,row['x'],row['y']),name) for name,poly in polys)
        measured.append(dict(row=row,gap_m=gap,zone=name))
first=next(item for item in measured if item['gap_m']<1.5)
worst=min(measured,key=lambda item:item['gap_m'])
onboard=[json.loads(line) for line in (out/'onboard.jsonl').read_text().splitlines()]
stamps=[item['stamp'] for item in onboard]
def observation(item):
    row=onboard[max(0,bisect.bisect_right(stamps,item['row']['t'])-1)]
    return {key:row.get(key) for key in ('stamp','mission','pose','velocity','red_timing','search_timing','observation')}
commands=[]
for line in (out/'flight_commands.jsonl').read_text().splitlines():
    row=json.loads(line)
    if first['row']['t']-2<=row['stamp']<=first['row']['t']+2:
        commands.append(row)
report=dict(scope='Independent simulator truth evaluation; never controller input',
    first_violation=first,minimum=worst,onboard_at_first=observation(first),
    onboard_at_minimum=observation(worst),commands_near_first=commands)
with (out/'red_clearance_review_20261007.json').open('x') as handle:json.dump(report,handle,indent=2)
print(json.dumps({key:report[key] for key in ('first_violation','minimum')},indent=2))
print(json.dumps(dict(first_stage=report['onboard_at_first']['mission'],minimum_stage=report['onboard_at_minimum']['mission'])))
