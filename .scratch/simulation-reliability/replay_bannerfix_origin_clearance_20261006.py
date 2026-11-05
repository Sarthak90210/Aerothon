"""Read-only captured onboard scan replay. No ROS nodes or simulator inputs.

The frozen SDF supplies only the static equipment mount. Aircraft pose, scan,
velocity and planner decisions come from the separately recorded onboard files.
Recorded pose sampling approximates the original controller's 25 Hz cache.
"""
import argparse
import ast
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/aerothon_avoidance/avoidance'))
from avoidance.local_planner import LocalPlanner
from avoidance.scan_geometry import register_rays


def build(out, fixture):
    records = []
    for line in (out / 'onboard.jsonl').open():
        row = json.loads(line)
        if row.get('mission') == 'RETURN_CORRIDOR':
            records.append(row)
    row = next(r for r in records if r['stamp'] >= 893.)
    decision = row['avoidance']
    scan_target = row['stamp'] - decision['scan_age_s']
    scan = None
    for line in (out / 'onboard_lidar.jsonl').open():
        candidate = json.loads(line)
        t = candidate['data']['header']['stamp']
        stamp = t['sec'] + t['nanosec'] * 1e-9
        if scan is None or abs(stamp-scan_target) < abs(scan[0]-scan_target):
            scan = stamp, candidate['data']
        if stamp > scan_target+.2:
            break
    capture = min(records, key=lambda r: abs(r['pose']['received_stamp']-scan[0]))
    pp = row['pose']['data']['pose']; cp = capture['pose']['data']['pose']
    q = pp['orientation']; cq = cp['orientation']
    yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))
    # Compile the existing controller method alone; do not import or construct
    # ROS objects, initialize middleware, or change any production method.
    source = ROOT / 'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'VelocityController')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'conditioned')
    namespace = {'math': math, 'np': np, '_RAD2DEG': 180/math.pi, '_DEG2RAD': math.pi/180}
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
    settings = dict(range_min_valid=.15,range_max_valid=12.,mask_sectors_deg=[150.,210.],median_window=3)
    controller = SimpleNamespace(_g=lambda key: settings[key])
    raw = SimpleNamespace(**scan[1]); raw.ranges = [float(v) for v in raw.ranges]
    bearings, ranges = namespace['conditioned'](controller,raw)
    hits = ranges < 11.999
    sdf = ET.parse(out/'flight_vehicle.sdf')
    mount = tuple(map(float,sdf.find('.//link[@name="base_scan"]/pose').text.split()[:3]))
    current_xy = [pp['position'][k] for k in ('x','y')]
    capture_xy = [cp['position'][k] for k in ('x','y')]
    origin,bearings,ranges = register_rays(bearings,ranges,mount,(0,0,0,1),capture_xy,
        [cq[k] for k in ('x','y','z','w')],current_xy,yaw)
    payload = dict(stamp=row['stamp'],scan_stamp=scan[0],pose_capture_error_s=abs(capture['pose']['received_stamp']-scan[0]),
        reported_clearance_m=decision['observed_clearance_m'],axis_bearing=0.,sensor_origin=origin.tolist(),
        bearings=bearings.tolist(),ranges=ranges.tolist(),hits=hits.tolist(),decision=decision)
    if fixture.exists(): raise FileExistsError(fixture)
    fixture.write_text(json.dumps(payload,indent=2)+'\n')


def replay(fixture):
    data=json.loads(fixture.read_text())
    p=LocalPlanner(occupied_radius=.4)
    p.observe(data['bearings'],data['ranges'],sensor_origin=data['sensor_origin'],hits=data['hits'])
    path=p.plan(data['axis_bearing'])
    report=dict(stamp=data['stamp'],clearance_m=float(p.distances([(0,0)])[0]),
        recorded_clearance_m=data['reported_clearance_m'],pose_capture_error_s=data['pose_capture_error_s'],
        start_known=bool(p.known([(0,0)])[0]),planner_reason=p.reason,path=path)
    print(json.dumps(report,indent=2))
    assert path, 'Captured feasible-course return is stuck at planner origin; no path can be certified'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('out',type=Path);parser.add_argument('fixture',type=Path)
    parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build: build(args.out,args.fixture)
    replay(args.fixture)
