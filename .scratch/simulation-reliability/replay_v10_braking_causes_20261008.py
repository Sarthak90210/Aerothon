import bisect,json,math,sys
from pathlib import Path
from types import SimpleNamespace
root=Path.cwd();sys.path.insert(0,str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.leg_router import LegRouter
run=root/'logs/reliability_reduced_v10_targeted_20261008/my_world_random_s3'
def rows(path):
 result=[]
 for s in path.read_text(encoding='utf-8').splitlines():
  try:result.append(json.loads(s))
  except ValueError:pass
 return result
observed=rows(run/'onboard.jsonl');stamps=[r['stamp'] for r in observed]
commands=[r for r in rows(run/'flight_commands.jsonl') if r['topic']=='/mavros/setpoint_position/local']
router=LegRouter();previous=None;events=[]
for cmd in commands:
 p=cmd['data']['pose']['position'];goal=(p['x'],p['y'])
 if goal==previous:continue
 i=bisect.bisect_right(stamps,cmd['stamp'])-1
 if i<0:continue
 r=observed[i];p=r.get('pose',{}).get('data',{}).get('pose',{}).get('position',{})
 if not p:continue
 at=(p['x'],p['y']);ex=r.get('red_timing',{}).get('exclusions',[])
 mav=SimpleNamespace(pos=lambda:at,exclusions=ex)
 if r.get('mission')=='SEARCH_QR' and previous is not None and math.dist(goal,at)<.15 and not router._segment_safe(mav,previous):
  events.append(dict(stamp=cmd['stamp'],at=at,old=previous,new=goal,old_distance=math.dist(previous,at),exclusions=len(ex)))
 previous=goal
print(json.dumps(dict(events=len(events),short_holds=sum(e['old_distance']<.5 for e in events),first=events[:8],last=events[-8:]),indent=2))
