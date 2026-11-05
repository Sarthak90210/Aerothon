"""Closed-loop fixture from preserved course, truth used only by raycasting/grading."""
import argparse, json, math, sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
import test_slalom_traverse as s
import numpy as np
import inspect, textwrap
from types import MethodType
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--tau',type=float,default=.6)
p.add_argument('--delay',type=float,default=.4);p.add_argument('--speed',type=float,default=.8)
p.add_argument('--noise',type=float,default=0.);p.add_argument('--seed',type=int,default=20261003)
p.add_argument('--scan-delay',type=float,default=0.)
p.add_argument('--body-delay',action='store_true')
p.add_argument('--mount',action='store_true')
p.add_argument('--entry-velocity',action='store_true')
p.add_argument('--rate-filter',type=float,default=0.)
p.add_argument('--cost-floor',type=float,default=0.)
a=p.parse_args();assert not a.out.exists()
out=root/'logs/reliability_render_my_world_s20261003_gustfix_20261006'
layout=json.loads((out/'layout.json').read_text());ox,oy,axis,length,width,height=layout['corridors']['return']
c,ss=math.cos(axis),math.sin(axis)
def fixture_xy(x,y):
    dx,dy=x-ox,y-oy;return 14-(c*dx+ss*dy),-4-(-ss*dx+c*dy)
s.WALLS=[s.rect(14-length/2,-4-width/2-.05,length+.2,.1),s.rect(14-length/2,-4+width/2+.05,length+.2,.1)]
s.BLOCKS=[]
for b in layout['obstacles']:
    pts=[fixture_xy(*v) for v in b['poly']];xs,ys=zip(*pts);s.BLOCKS.append((min(xs),max(xs),min(ys),max(ys)))
entry=next(json.loads(v) for v in (out/'onboard.jsonl').open() if json.loads(v).get('mission')=='RETURN_CORRIDOR')
pose=entry['pose']['data']['pose'];q=pose['orientation'];px=pose['position'];hx,hy=layout['home_world']
x,y=fixture_xy(px['x']+hx,px['y']+hy);yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))-(axis-math.pi)
case=s.SlalomTraverseTests('test_the_return_slalom_is_flown_without_contact');case.setUpClass();case.setUp();case.node.cruise=a.speed
if a.cost_floor:
    method=case.node._planner.plan.__func__;code=textwrap.dedent(inspect.getsource(method));old='max(0.05, float(d)-self.clearance)';assert code.count(old)==1
    code=code.replace(old,f'max({a.cost_floor!r}, float(d)-self.clearance)');namespace=dict(method.__globals__);exec(compile(code,'<diagnostic clearance cost>','exec'),namespace);case.node._planner.plan=MethodType(namespace['plan'],case.node._planner)
if a.rate_filter:
    method=case.node._compensated.__func__;code=textwrap.dedent(inspect.getsource(method));old='self._wind_rate_world += (rate-self._wind_rate_world)*f';assert code.count(old)==1
    code=code.replace(old,f'self._wind_rate_world += (rate-self._wind_rate_world)*min(1.,span/{a.rate_filter!r})');namespace=dict(method.__globals__);exec(compile(code,'<diagnostic rate filter>','exec'),namespace);case.node._compensated=MethodType(namespace['_compensated'],case.node)
if a.mount:
    from geometry_msgs.msg import TransformStamped
    from tf2_ros import Buffer
    original_scan=s.scan_at
    def mounted_scan(x,y,yaw,rects):
        scan=original_scan(x+.138933*math.cos(yaw)+.002257*math.sin(yaw),y+.138933*math.sin(yaw)-.002257*math.cos(yaw),yaw,rects)
        scan.header.frame_id='base_scan';return scan
    s.scan_at=mounted_scan
    t=TransformStamped();t.header.frame_id='base_link';t.child_frame_id='base_scan';t.transform.translation.x=.138933;t.transform.translation.y=-.002257;t.transform.translation.z=.0815;t.transform.rotation.w=1.
    case.node._tf_buffer=Buffer();case.node._tf_buffer.set_transform_static(t,'recorded_relative_mount')
    s.N_BEAMS=450
if a.body_delay or a.entry_velocity:
    method=case.fly.__func__;code=textwrap.dedent(inspect.getsource(method))
    if a.body_delay:
        code=code.replace('commands.append((t+command_delay_s,(cvx,cvy)))','commands.append((t+command_delay_s,(vx,vy)))')
        code=code.replace('applied=commands.pop(0)[1]','avx,avy=commands.pop(0)[1]\n            applied=(avx*math.cos(yaw)-avy*math.sin(yaw),avx*math.sin(yaw)+avy*math.cos(yaw))')
    if a.entry_velocity:
        v=entry['velocity']['data']['twist']['linear'];ivx=-(c*v['x']+ss*v['y']);ivy=ss*v['x']-c*v['y']
        code=code.replace('wvx = wvy = 0.0',f'wvx,wvy = {ivx!r},{ivy!r}')
    namespace=dict(method.__globals__);exec(compile(code,'<body transport fixture>','exec'),namespace);case.fly=MethodType(namespace['fly'],case)
rows=[];publish=case.node._publish
def capture(*args,**kw):
    publish(*args,**kw);px,py=case.node._pos;rows.append(dict(t=case.node._now(),x=px,y=py,clearance=min(s.gap_to(px,py,r) for r in s.WALLS+s.BLOCKS),detail=case.node.last_detail))
case.node._publish=capture
rng=np.random.default_rng(a.seed)
def corrupt(ranges):
    r=np.array(ranges);valid=np.isfinite(r);r[valid]+=rng.normal(0,a.noise,valid.sum());return r
try:
    _,closest,_=case.fly(x,y,yaw,goal_x=3.5,vel_tau_s=a.tau,command_delay_s=a.delay,corrupt=corrupt if a.noise else None,scan_delay_s=a.scan_delay)
    case.assertGreaterEqual(closest,.70);passed=True;failure=None
except AssertionError as e:passed=False;failure=str(e)
finally:
    a.out.write_text(json.dumps(dict(passed=passed,failure=failure,rows=rows,entry=[x,y,yaw],tau=a.tau,delay=a.delay,speed=a.speed,entry_velocity=a.entry_velocity,rate_filter_s=a.rate_filter,mount=a.mount,body_delay=a.body_delay,noise=a.noise,scan_delay=a.scan_delay,seed=a.seed))+'\n')
    print(json.dumps(dict(passed=passed,minimum=min(r['clearance'] for r in rows),rows=len(rows),failure=failure)))
    case.tearDown();case.tearDownClass()
raise SystemExit(0 if passed else 1)
