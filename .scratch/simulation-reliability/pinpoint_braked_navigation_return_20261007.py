"""Independent read-only return handover review; truth stays in evaluation."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sim'))
from check_track import load_track, lanes, to_lane, rect_gap
from qualification_evidence import recorded_disarm

p = argparse.ArgumentParser()
p.add_argument('--run', type=Path, default=ROOT / 'logs/reliability_corrected_headless_focus_20261007/my_world_calm_s1')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
assert not a.out.exists(), 'Preserve previous reports'
layout = json.loads((a.run / 'layout.json').read_text())
track = load_track(a.run / 'evaluation_truth_track.csv')
onboard = [json.loads(line) for line in (a.run / 'onboard.jsonl').read_text().splitlines()]
commands = [json.loads(line) for line in (a.run / 'flight_commands.jsonl').read_text().splitlines()]

def stamp(data):
    h = data.get('header', {}).get('stamp', {})
    return h.get('sec', 0) + h.get('nanosec', 0) * 1e-9

def clearance(row):
    values = []
    for i, lane in enumerate(lanes(layout)):
        u, v = to_lane(row, layout, lane)
        if 0 <= u <= lane[3] and abs(v) <= lane[4] / 2 and row['z'] < lane[5]:
            values.append(dict(m=lane[4]/2-abs(v), source=f'corridor_{i}_wall', u=u, v=v))
    hx, hy = layout.get('home_world', [0, 0])
    for i, obstacle in enumerate(layout.get('obstacles', [])):
        if row['z'] < obstacle['h'] + .3:
            gap = rect_gap([(x-hx, y-hy) for x, y in obstacle['poly']], row['x'], row['y'])
            values.append(dict(m=gap, source=f'obstacle_{i}'))
    return min(values, key=lambda v: v['m']) if values else None

def observed(row):
    d = row.get('pose', {}).get('data', {})
    pos = d.get('pose', {}).get('position', {})
    q = d.get('pose', {}).get('orientation', {})
    if pos and q:
        yaw = math.atan2(2*(q['w']*q['z'] + q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))
    else: yaw = None
    vel = row.get('velocity', {}).get('data', {})
    return dict(recorded_stamp=row['stamp'], mission=row.get('mission'),
        pose_capture=stamp(d), position=pos, yaw_rad=yaw,
        velocity_capture=stamp(vel), velocity=vel.get('twist', {}).get('linear'),
        avoidance=row.get('avoidance'))

def command(row):
    d = row['data']
    if row['topic'] == '/mavros/setpoint_position/local':
        payload = d['pose']
    else:
        payload = {k:d[k] for k in ('coordinate_frame', 'type_mask', 'velocity', 'yaw_rate')}
    return dict(header_stamp=stamp(d), recorder_stamp=row['stamp'], topic=row['topic'], payload=payload)

physical = [dict(row=r, clearance=clearance(r)) for r in track if r['armed'] and r['z'] > .3]
first = next(r for r in physical if r['clearance'] and r['clearance']['m'] < .7)
minimum = min((r for r in physical if r['clearance']), key=lambda r:r['clearance']['m'])
return_rows = [r for r in onboard if 757.5599999990001 <= r['stamp'] <= 777.5599999990001]
transitions = []
last = None
for row in onboard:
    mission = row.get('mission')
    if mission != last:
        if 737.5599999990001 <= row['stamp'] <= 797.5599999990001: transitions.append(observed(row))
        last = mission

raw = [r for r in commands if r['topic'] == '/mavros/setpoint_raw/local' and 757.5599999990001 <= stamp(r['data']) <= 777.5599999990001]
pos = [r for r in commands if r['topic'] == '/mavros/setpoint_position/local' and 757.5599999990001 <= stamp(r['data']) <= 777.5599999990001]
physical_window = [r for r in physical if 765.5599999990001 <= r['row']['t'] <= 772.5599999990001]
result = dict(run=str(a.run), independent_truth_first_below_070=first,
    independent_truth_minimum=minimum, independent_truth_return_window=physical_window,
    mission_transitions=transitions, onboard_return_window=[observed(r) for r in return_rows],
    position_commands= [command(r) for r in pos], raw_commands=[command(r) for r in raw],
    recorded_disarm=recorded_disarm(onboard),
    limits=['Truth geometry here is for independent evaluation only.',
            'Command headers are transmission times; recorder stamps are independent DDS callback times.',
            'The actual world command callback time and pending queue contents were not recorded.',
            'Avoidance details are cached recorder observations without their own capture stamps.'])
result['independent_target_evaluation'] = []
for cmd in result['position_commands'][-8:]:
    pos = cmd['payload']['position']
    result['independent_target_evaluation'].append(dict(command=cmd, clearance=clearance(pos)))
return_raw = [r for r in commands if r['topic'] == '/mavros/setpoint_raw/local' and stamp(r['data']) >= 766.5599999990001]
result['return_raw_command_counts'] = dict(total=len(return_raw),
    zero_horizontal=sum(math.hypot(r['data']['velocity']['x'],r['data']['velocity']['y']) < 1e-9 for r in return_raw),
    maximum_horizontal_mps=max((math.hypot(r['data']['velocity']['x'],r['data']['velocity']['y']) for r in return_raw),default=0.))
a.out.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k:result[k] for k in ('independent_truth_first_below_070', 'independent_truth_minimum', 'mission_transitions', 'recorded_disarm')}, indent=2))
print('return raw first10', json.dumps(result['raw_commands'][:10], indent=2))
print('position last8', json.dumps(result['position_commands'][-8:], indent=2))
