"""Replay saved commands against unchanged physical methods, without flight nodes.

World callback times were not recorded. Header and independent-recorder times
are alternative callback proxies, not an exact replay of DDS scheduling.
"""
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sim'))
import headless_world as H
from check_track import load_track, lanes, rect_gap, to_lane

RUN = ROOT / 'logs/reliability_corrected_headless_focus_20261007/my_world_calm_s1'
OUT = ROOT / '.scratch/simulation-reliability/headless_handover_motion_replay_20261007.json'
assert not OUT.exists(), 'Preserve earlier replay'
manifest=json.loads((RUN/'source_manifest.json').read_text())
source_hash=hashlib.sha256((ROOT/'sim/headless_world.py').read_bytes()).hexdigest()
assert manifest['sim/headless_world.py'] == source_hash, 'Use focus physical source only'
rows=[json.loads(l) for l in (RUN/'onboard.jsonl').read_text().splitlines()]
commands=[json.loads(l) for l in (RUN/'flight_commands.jsonl').read_text().splitlines()]
layout=json.loads((RUN/'layout.json').read_text())
spec=H.W.load(RUN/'world_spec.json')
truth=load_track(RUN/'evaluation_truth_track.csv')

def stamp(data):
    s=data.get('header',{}).get('stamp',{})
    return s.get('sec',0)+s.get('nanosec',0)*1e-9

start=next(r for r in rows if 833.27 <= stamp(r.get('pose',{}).get('data',{})) <= 833.29)
start_t=stamp(start['pose']['data'])
initial_p=start['pose']['data']['pose']['position']
initial_v=start['velocity']['data']['twist']['linear']
q=start['pose']['data']['pose']['orientation']
initial_yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))

def gap(p):
    row=dict(x=float(p[0]),y=float(p[1]),z=float(p[2]))
    values=[]
    for lane in lanes(layout):
        u,v=to_lane(row,layout,lane)
        if 0<=u<=lane[3] and abs(v)<=lane[4]/2 and p[2]<lane[5]:values.append(lane[4]/2-abs(v))
    hx,hy=layout['home_world']
    for obstacle in layout['obstacles']:
        if p[2]<obstacle['h']+.3:
            values.append(rect_gap([(x-hx,y-hy) for x,y in obstacle['poly']],p[0],p[1]))
    return min(values)

def make_world():
    w=H.HeadlessWorld.__new__(H.HeadlessWorld)
    w.lock=threading.Lock()
    w.args=SimpleNamespace(vel_command_delay_s=.4,vel_response_s=.6)
    w.t=start_t
    w.p=np.array([initial_p[k] for k in ('x','y','z')])
    w.v=np.array([initial_v[k] for k in ('x','y','z')])
    w.ground_velocity=w.v.copy()
    w.yaw=initial_yaw
    w.roll=w.pitch=0.
    w.mode='GUIDED';w.armed=True
    w.sp_pos=w.sp_vel=w.takeoff_alt=None
    w.pending_velocity=deque();w.speed_cap=H.WPNAV_SPEED;w.wind=None
    w.arena=H.Arena(spec,'b');w.contacts=[];w.events=[];w.params={}
    w.fence_poly=None;w.fence_breaches=0;w.landed_t=None
    w.est=lambda:w.p.copy()
    w._event=lambda event:w.events.append((w.t,event))
    return w

def deliver(w,row):
    d=row['data']
    if row['topic']=='/mavros/setpoint_position/local':
        p=d['pose']['position'];q=d['pose']['orientation']
        w._on_sp_pos(SimpleNamespace(pose=SimpleNamespace(position=SimpleNamespace(**p),orientation=SimpleNamespace(**q))))
    else:
        w._on_sp_raw(SimpleNamespace(velocity=SimpleNamespace(**d['velocity']),yaw_rate=d['yaw_rate'],coordinate_frame=d['coordinate_frame']))

def replay(proxy):
    w=make_world()
    def received(row):return stamp(row['data']) if proxy=='header' else row['stamp']
    packets=sorted([r for r in commands if r['topic'] in ('/mavros/setpoint_position/local','/mavros/setpoint_raw/local')
                    and 832. <= received(r) <= 837.],key=received)
    idx=0
    # Prime the real position controller with its last received target.
    while idx<len(packets) and received(packets[idx])<=w.t+1e-9:
        deliver(w,packets[idx]);idx+=1
    samples=[]
    while w.t<837.-1e-9:
        while idx<len(packets) and received(packets[idx])<=w.t+1e-9:
            deliver(w,packets[idx]);idx+=1
        w._step_airframe();w.t+=H.DT
        samples.append(dict(t=w.t,p=w.p.tolist(),v=w.ground_velocity.tolist(),clearance_m=gap(w.p),
            control='position' if w.sp_pos is not None else 'raw_velocity',pending_packets=len(w.pending_velocity)))
    minimum=min(samples,key=lambda r:r['clearance_m'])
    first=next((r for r in samples if r['clearance_m']<.7),None)
    first_raw=next((r for r in samples if r['control']=='raw_velocity'),None)
    reference=[r for r in truth if start_t<=r['t']<=837.]
    errors=[]
    for r in reference:
        s=min(samples,key=lambda s:abs(s['t']-r['t']))
        errors.append(math.dist(s['p'],[r[k] for k in ('x','y','z')]))
    return dict(callback_time_proxy=proxy,first_below_070=first,minimum=minimum,first_raw_ownership=first_raw,
        contacts=w.contacts,truth_comparison=dict(samples=len(errors),mean_position_error_m=float(np.mean(errors)),max_position_error_m=max(errors)),
        samples=samples)

report=dict(kind='physical callback-proxy replay, not exact DDS reproduction',
    original_run=str(RUN),headless_source_sha256=source_hash,initial_onboard_record=start,
    delay_s=.4,response_s=.6,wind='original calm zero; unchanged physical integration',
    results=[replay('header'),replay('recorder')],
    limits=['Initial state is actual saved onboard pose/FCU ground velocity in a zero-noise calm run.',
            'Saved position/raw commands are open-loop inputs; no new mission or perception decision is executed.',
            'World callback times are missing; both proxies are assumptions, not measured transport.',
            'World geometry is used only by the physical collision model and separate clearance evaluation.',
            'No timeout, stopping test, or proxy agreement counts as a corridor traversal or mission pass.'])
OUT.write_text(json.dumps(report,indent=2)+'\n')
for result in report['results']:
    print(json.dumps({k:result[k] for k in ('callback_time_proxy','first_below_070','minimum','first_raw_ownership','truth_comparison','contacts')},indent=2))
