import bisect,json,math,re,sys
from pathlib import Path
from types import SimpleNamespace
root=Path.cwd();sys.path.insert(0,str(root/'src/aerothon_mission/mission_bt'))
from mission_bt.leg_router import LegRouter
from mission_bt.search_planner import routing_obstacles,path_hits_exclusion,point_in_exclusion
run=root/'logs/reliability_reduced_v15_targeted_20261008/my_world_random_s3'
offset=None
rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
rows=[r for r in rows if 'received_wall_s' in r.get('pose',{})];walls=[r['pose']['received_wall_s'] for r in rows]
from statistics import median
pairs=[]
for line in (run/'stack.log').read_text(encoding='utf-8').splitlines():
 match=re.search(r'\[([0-9.]+)\] \[headless_world\]: \[t=\s*([0-9.]+)\]',line)
 if match:
  sim=float(match[2]);row=min(rows,key=lambda r:abs(r['stamp']-sim))
  if abs(row['stamp']-sim)<.25:pairs.append(float(match[1])-row['pose']['received_wall_s'])
offset=median(pairs);print('approximate offset from paired world events',offset,'samples',len(pairs))
commands=[]
for s in (run/'flight_commands.jsonl').read_text(encoding='utf-8').splitlines():
 try:r=json.loads(s)
 except ValueError:continue
 if r['topic']=='/mavros/setpoint_position/local':commands.append(r)
stamps=[r['stamp'] for r in commands];events=[];router=LegRouter()
for line in (run/'stack.log').read_text(encoding='utf-8').splitlines():
 if 'search segment invalidated' not in line:continue
 stamp=float(re.search(r'\[INFO\] \[([0-9.]+)\]',line)[1])-offset
 i=bisect.bisect_right(walls,stamp)-1
 if i<0:continue
 r=rows[i];p=r['pose']['data']['pose']['position'];at=(p['x'],p['y']);ex=r.get('red_timing',{}).get('exclusions',[])
 v=r['velocity']['data']['twist']['linear'];speed=math.hypot(v['x'],v['y'])
 # Last issued command before the next simulator sample approximates the old intent.
 j=bisect.bisect_left(stamps,r['stamp'])-1
 if j<0:continue
 p=commands[j]['data']['pose']['position'];goal=(p['x'],p['y'])
 mav=SimpleNamespace(pos=lambda:at,exclusions=ex)
 blocks=routing_obstacles(ex,1.5)
 def gap(rect,p):
  x0,x1,y0,y1=rect;return math.hypot(p[0]-min(max(p[0],x0),x1),p[1]-min(max(p[1],y0),y1))
 n=max(2,int(math.dist(at,goal)/.02)+2)
 raw_gap=min((gap(rect,(at[0]+(goal[0]-at[0])*k/(n-1),at[1]+(goal[1]-at[1])*k/(n-1))) for rect in ex for k in range(n)),default=None)
 raw_safe=not point_in_exclusion(*at,1.5,ex) and not point_in_exclusion(*goal,1.5,ex) and not path_hits_exclusion([at,goal],1.5,ex)
 events.append(dict(exact_raw_safe=raw_safe,sim_stamp=r['stamp'],host_alignment_error_s=stamp-walls[i],at=at,goal=goal,distance=math.dist(at,goal),speed=speed,exclusions=len(ex),guard_rejects=not router._segment_safe(mav,goal),raw_sampled_clearance_m=raw_gap,merged_containing=[b for b in blocks if b[0]<=at[0]<=b[1] and b[2]<=at[1]<=b[3]]))
review=dict(approximate_alignment=True,exact_raw_safe=sum(e['exact_raw_safe'] for e in events),time_offset=offset,total=len(events),short_intents=sum(e['distance']<.5 for e in events),short_with_motion_above_settled=sum(e['distance']<.5 and e['speed']>.1 for e in events),events=events)
(run/'braking_command_replay.json').write_text(json.dumps(review,indent=2))
print(json.dumps({k:v for k,v in review.items() if k!='events'}));print(json.dumps(events[:5]+events[-5:],indent=2))
