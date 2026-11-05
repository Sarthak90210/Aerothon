"""Actual conditioned/registered native scan at the safe-origin stop boundary.

The original high-rate attitude cache is sampled by the onboard recorder.
This seam preserves recorded velocity registration and notes the attitude
sampling error; it does not reconstruct original ROS callback ordering.
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

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'src/aerothon_avoidance/avoidance'))
from avoidance.fast_connected_planner_candidate import FastConnectedPlanner as LocalPlanner
from avoidance.scan_geometry import register_rays

run=root/'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
fixture=root/'.scratch/simulation-reliability/v38_native_origin_20261009.json'
source=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
def build():
    rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
    rows=[row for row in rows if 'pose' in row]
    candidates=[row for row in rows if row.get('mission')=='RETURN_CORRIDOR'
        and .705<row.get('avoidance',{}).get('observed_clearance_m',math.inf)<.722]
    assert candidates
    row=candidates[0];detail=row['avoidance']
    target=row['stamp']-detail['scan_age_s']
    scans=[json.loads(line) for line in (run/'onboard_lidar.jsonl').read_text(encoding='utf-8').splitlines()]
    def stamp(scan):
        value=scan['data']['header']['stamp'];return value['sec']+value['nanosec']*1e-9
    scan=min(scans,key=lambda item:abs(stamp(item)-target))
    capture=min(rows,key=lambda item:abs(item['pose']['received_stamp']-stamp(scan)))
    cls=next(item for item in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(item,ast.ClassDef) and item.name=='VelocityController')
    method=next(item for item in cls.body if isinstance(item,ast.FunctionDef) and item.name=='conditioned')
    namespace=dict(math=math,np=np,_RAD2DEG=180/math.pi,_DEG2RAD=math.pi/180)
    exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
    settings=dict(range_min_valid=.15,range_max_valid=12.,mask_sectors_deg=[150.,210.],median_window=3)
    node=SimpleNamespace(_g=lambda key:settings[key])
    raw=SimpleNamespace(**scan['data']);raw.ranges=[float(value) for value in raw.ranges]
    bearings,ranges=namespace['conditioned'](node,raw)
    hits=ranges<11.999
    mount=tuple(map(float,ET.parse(run/'flight_vehicle.sdf').find('.//link[@name="base_scan"]/pose').text.split()[:3]))
    pose=row['pose']['data']['pose'];q=pose['orientation']
    cp=capture['pose']['data']['pose'];cq=cp['orientation']
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2))
    capture_xy=np.array([cp['position'][key] for key in ('x','y')])
    current_xy=capture_xy+np.array(detail['scan_motion_world_m'])
    origin,bearings,ranges=register_rays(bearings,ranges,mount,(0,0,0,1),capture_xy,
        [cq[key] for key in ('x','y','z','w')],current_xy,yaw)
    payload=dict(recorded_stamp=row['stamp'],scan_capture_stamp=stamp(scan),
        attitude_sampling_error_s=abs(capture['pose']['received_stamp']-stamp(scan)),
        recorded_clearance_m=detail['observed_clearance_m'],sensor_origin=origin.tolist(),
        bearings=bearings.tolist(),ranges=ranges.tolist(),hits=hits.tolist(),
        recorded_detail=detail,source_run=str(run.relative_to(root)),
        limitation='Onboard attitude sampling, not exact original high-rate callback replay')
    fixture.write_text(json.dumps(payload,indent=2))

def replay():
    payload=json.loads(fixture.read_text())
    planner=LocalPlanner(occupied_radius=.4)
    planner.observe(payload['bearings'],payload['ranges'],sensor_origin=payload['sensor_origin'],hits=payload['hits'])
    gap=float(planner.distances([(0,0)])[0])
    path=planner.plan(0)
    report=dict(recorded_stamp=payload['recorded_stamp'],recorded_clearance_m=payload['recorded_clearance_m'],
        replayed_clearance_m=gap,attitude_sampling_error_s=payload['attitude_sampling_error_s'],
        planner_reason=planner.reason,actual_path=path,known_origin=bool(planner.known([(0,0)])[0]))
    print(json.dumps(report),flush=True)
    assert abs(gap-payload['recorded_clearance_m'])<.005,'Registration approximation does not reproduce the recorded clearance'
    assert gap>=.70,'This fixture must isolate a still-safe observed origin'
    assert path,'Actual captured safe-origin return scan is rejected before any route is searched'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build:build()
    replay()
