"""Replay recorded onboard publication inputs; simulator truth is not read."""
import argparse
import bisect
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rclpy
from rclpy.parameter import Parameter
from sensor_msgs.msg import LaserScan

p = argparse.ArgumentParser()
p.add_argument('recording', type=Path)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--stamp', type=float, default=457.5)
p.add_argument('--budget', type=float)
p.add_argument('--require-rejection', action='store_true')
args = p.parse_args()
sys.path.insert(0, str(args.source/'src/aerothon_avoidance/avoidance'))
from avoidance.velocity_controller import VelocityController
from avoidance.scan_geometry import register_rays

def yaw(pose):
    q = pose['orientation']
    return math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))

rows = [json.loads(line) for line in (args.recording/'onboard.jsonl').open()]
row = min(rows, key=lambda r: abs(r['stamp']-args.stamp))
d = row['avoidance']
assert row['mission'] == 'RETURN_CORRIDOR' and d['state'] == 'CRUISE'
t = row['stamp']
scan_target = t-d['scan_age_s']
scans = [json.loads(line)['data'] for line in (args.recording/'onboard_lidar.jsonl').open()]
stamp = lambda data: data['header']['stamp']['sec']+data['header']['stamp']['nanosec']*1e-9
data = min(scans, key=lambda data: abs(stamp(data)-scan_target))
pose_rows = [r for r in rows if r.get('pose')]
capture = min(pose_rows, key=lambda r: abs(stamp(r['pose']['data'])-stamp(data)))
pp = row['pose']['data']['pose']
cp = capture['pose']['data']['pose']
pose_times = [r['stamp'] for r in pose_rows]
commands = [json.loads(line) for line in (args.recording/'flight_commands.jsonl').open()]
commands = [r for r in commands if r['topic'] == '/mavros/setpoint_raw/local' and r['data']['type_mask'] == 1479 and t-4 <= r['stamp'] <= t]
packet = min(commands, key=lambda r: abs(r['stamp']-t))['data']
rclpy.init()
c = VelocityController()
try:
    if args.budget is not None:
        c.set_parameters([Parameter('motion_computation_budget_s', value=args.budget)])
    c._now = lambda: t
    c._pos = tuple(pp['position'][k] for k in ('x', 'y'))
    c._yaw = yaw(pp)
    c._pose_t = t-d['pose_age_s']
    c._scan_t = stamp(data)
    c._fcu_velocity_t = t-d['fcu_velocity_age_s']
    c._fcu_velocity = np.array(d['ground_velocity_world_mps'])
    c._ground_world = c._fcu_velocity.copy()
    c._wind_world = np.array(d['disturbance_world_mps'])
    c._wind_rate_world = np.array(d['disturbance_rate_world_mps2'])
    c._response_known = True
    c.state = 'CRUISE'
    c._velocity_fault = ''
    c.scan = LaserScan()
    for name in ('angle_min', 'angle_max', 'angle_increment', 'range_min', 'range_max', 'scan_time', 'time_increment'):
        if name in data:
            setattr(c.scan, name, float(data[name]))
    c.scan.ranges = [float(v) for v in data['ranges']]
    bearings, ranges = c.conditioned(c.scan)
    hits = ranges < float(c._g('range_max_valid'))-.001
    mount = tuple(map(float, ET.parse(args.recording/'flight_vehicle.sdf').find('.//link[@name="base_scan"]/pose').text.split()[:3]))
    origin, bearings, ranges = register_rays(bearings, ranges, mount, (0, 0, 0, 1),
        [cp['position'][k] for k in ('x', 'y')], [cp['orientation'][k] for k in ('x', 'y', 'z', 'w')], c._pos, c._yaw)
    c._planner.observe(bearings, ranges, sensor_origin=origin, hits=hits)
    c._command_history.clear()
    for command in commands:
        r = pose_rows[max(0, bisect.bisect_right(pose_times, command['stamp'])-1)]
        heading = yaw(r['pose']['data']['pose'])
        v = command['data']['velocity']
        co, si = math.cos(heading), math.sin(heading)
        c._command_history.append((command['stamp'], np.array([co*v['x']-si*v['y'], si*v['x']+co*v['y']])))
        c._sent_heading[command['stamp']] = heading
        c._yaw_command_history.append((command['stamp'], command['data']['yaw_rate']))
    command = tuple(packet['velocity'][k] for k in ('x', 'y'))
    c._compensated = lambda vx, vy: command
    sent = []
    c.pub_sp.publish = sent.append
    c._publish(*command, d['front_m'], math.radians(d['gap_bearing_deg']), {})
    result = dict(stamp=t, recorded_command=command, replay_command=[sent[-1].velocity.x, sent[-1].velocity.y],
        replay_detail=c.last_detail, capture_pose_pair_error_s=abs(stamp(capture['pose']['data'])-stamp(data)),
        scope='Onboard replay, approximate recorded pose sampling; no simulator truth inputs')
    print(json.dumps(result, indent=2))
    if args.require_rejection:
        assert 'recovery_reason' in c.last_detail, 'Recorded travel pulse still certified near the failed return bottleneck'
finally:
    c.destroy_node()
    rclpy.shutdown()
