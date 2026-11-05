"""Read independent live clearance; final disarm grading remains authoritative."""
import bisect,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'scripts')]
from check_track import lanes,to_lane,rect_gap,red_polygons
from native_contact_evidence import qualify_vehicle_contacts

def read_rows(path):
 rows=[]
 if path.exists():
  for line in path.read_text(encoding='utf-8').splitlines():
   try:rows.append(json.loads(line))
   except ValueError:pass
 return rows
for out in sorted((root/'logs').glob('reliability_reduced_v16_render_*_20261008')):
 layout_path=out/'layout.json'
 if not layout_path.exists():continue
 layout=json.loads(layout_path.read_text());onboard=read_rows(out/'onboard.jsonl');truth=read_rows(out/'evaluation_vehicle_truth.jsonl');onboard=[r for r in onboard if 'flight' in r];times=[r['stamp'] for r in onboard];gap=[];red=[];hx,hy=layout.get('home_world',[0,0]);count=0
 for pose in truth:
  i=bisect.bisect_right(times,pose['stamp'])-1
  if i<0 or not onboard[i]['flight']['data']['armed'] or pose['z']<=.3:continue
  count+=1;r=dict(t=pose['stamp'],x=pose['x']-hx,y=pose['y']-hy,z=pose['z'])
  for lane in lanes(layout):
   u,v=to_lane(r,layout,lane)
   if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and r['z']<lane[5]:gap.append((lane[4]/2-abs(v),pose['stamp']))
  for obstacle in layout.get('obstacles',[]):
   if r['z']<obstacle['h']+.3:gap.append((rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],r['x'],r['y']),pose['stamp']))
  for _,poly in red_polygons(layout):red.append((rect_gap(poly,r['x'],r['y']),pose['stamp']))
 contact_rows=read_rows(out/'evaluation_vehicle_contacts.jsonl')
 heartbeat=max((r['stamp'] for r in contact_rows if r.get('kind')=='heartbeat'),default=-1)
 contact_evidence=qualify_vehicle_contacts(out,[r for r in onboard if r['stamp']<=heartbeat],truth,layout)
 print(json.dumps(dict(run=out.name,latest_stamp=truth[-1]['stamp'] if truth else None,mission=onboard[-1].get('mission') if onboard else None,airborne_truth_samples=count,minimum_corridor= min(gap) if gap else None,minimum_red=min(red) if red else None,live_contact_evidence=contact_evidence,qualified=False)))
