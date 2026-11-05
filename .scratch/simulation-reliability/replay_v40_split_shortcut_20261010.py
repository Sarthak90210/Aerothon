"""Actual registered native scan where the V40 split return grazed the board.

Rebuilds the controller's own conditioned and registered observation from the
recorded journals at the tick the independent minimum occurred, then replays
it through both planners and measures the route they choose. The onboard
recorder samples attitude, so this preserves the recorded velocity
registration and notes the sampling error; it does not reconstruct the
original high-rate ROS callback ordering.

    python3 .scratch/simulation-reliability/replay_v40_split_shortcut_20261010.py --build
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

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'src/aerothon_avoidance/avoidance'))
from avoidance.local_planner import LocalPlanner                       # noqa: E402
from avoidance.fast_connected_planner_candidate import FastConnectedPlanner  # noqa: E402
from avoidance.scan_geometry import register_rays                      # noqa: E402

run = root/'logs/reliability_reduced_v40_render_split_corridors_s20261003_20261010'
fixture = root/'sim/fixtures/corridor_native_slalom_shortcut_split_s20261003_20261010.json'
source = root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'


def build():
    rows = [json.loads(line) for line in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
    rows = [row for row in rows if 'pose' in row]
    # The tick that steered into the independent minimum: inside the slalom
    # station, already under the planning reserve, still cruising.
    candidates = [row for row in rows
                  if row.get('mission') == 'RETURN_CORRIDOR'
                  and 408.3 <= row['stamp'] <= 408.7
                  and (row.get('avoidance') or {}).get('observed_clearance_m') is not None]
    assert candidates, 'No recorded RETURN_CORRIDOR tick at the clearance minimum'
    row = min(candidates, key=lambda item: item['avoidance']['observed_clearance_m'])
    detail = row['avoidance']
    target = row['stamp']-detail['scan_age_s']
    scans = [json.loads(line) for line in (run/'onboard_lidar.jsonl').read_text(encoding='utf-8').splitlines()]

    def stamp(scan):
        value = scan['data']['header']['stamp']
        return value['sec']+value['nanosec']*1e-9

    scan = min(scans, key=lambda item: abs(stamp(item)-target))
    capture = min(rows, key=lambda item: abs(item['pose']['received_stamp']-stamp(scan)))
    cls = next(item for item in ast.parse(source.read_text(encoding='utf-8')).body
               if isinstance(item, ast.ClassDef) and item.name == 'VelocityController')
    method = next(item for item in cls.body
                  if isinstance(item, ast.FunctionDef) and item.name == 'conditioned')
    namespace = dict(math=math, np=np, _RAD2DEG=180/math.pi, _DEG2RAD=math.pi/180)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
    settings = dict(range_min_valid=.15, range_max_valid=12., mask_sectors_deg=[150., 210.],
                    median_window=3)
    node = SimpleNamespace(_g=lambda key: settings[key])
    raw = SimpleNamespace(**scan['data'])
    raw.ranges = [float(value) for value in raw.ranges]
    bearings, ranges = namespace['conditioned'](node, raw)
    hits = ranges < 11.999
    mount = tuple(map(float, ET.parse(run/'flight_vehicle.sdf')
                      .find('.//link[@name="base_scan"]/pose').text.split()[:3]))
    pose = row['pose']['data']['pose']
    q = pose['orientation']
    cp = capture['pose']['data']['pose']
    cq = cp['orientation']
    yaw = math.atan2(2*(q['w']*q['z']+q['x']*q['y']), 1-2*(q['y']**2+q['z']**2))
    capture_xy = np.array([cp['position'][key] for key in ('x', 'y')])
    current_xy = capture_xy+np.array(detail['scan_motion_world_m'])
    origin, bearings, ranges = register_rays(bearings, ranges, mount, (0, 0, 0, 1), capture_xy,
                                             [cq[key] for key in ('x', 'y', 'z', 'w')],
                                             current_xy, yaw)
    payload = dict(
        recorded_stamp=row['stamp'], scan_capture_stamp=stamp(scan),
        attitude_sampling_error_s=abs(capture['pose']['received_stamp']-stamp(scan)),
        recorded_clearance_m=detail['observed_clearance_m'],
        recorded_path_body_m=detail.get('planner_path_body_m'),
        sensor_origin=origin.tolist(), bearings=bearings.tolist(), ranges=ranges.tolist(),
        hits=hits.tolist(), recorded_detail=detail, source_run=str(run),
        independent_minimum_clearance_m=json.loads(
            (run/'clearance_diagnosis.json').read_text())['minimum_clearance_m'],
        limitation='Onboard attitude sampling, not exact original high-rate callback replay')
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(payload, indent=2))


def route(planner_type, payload):
    planner = planner_type(occupied_radius=.4)
    planner.observe(payload['bearings'], payload['ranges'],
                    sensor_origin=payload['sensor_origin'], hits=payload['hits'])
    gap = float(planner.distances([(0, 0)])[0])
    path = planner.plan(0)
    dense = (np.concatenate([np.linspace(a, b, 2001) for a, b in zip(path, path[1:])])
             if len(path) > 1 else np.array([[0., 0.]]))
    return dict(planner=planner_type.__name__, origin_clearance_m=gap, reason=planner.reason,
                path=path, waypoints=len(path),
                route_minimum_clearance_m=float(planner.distances(dense).min()),
                route_known=bool(planner.known(dense).all()),
                first_segment_m=math.dist(path[0], path[1]) if len(path) > 1 else 0.)


def replay():
    payload = json.loads(fixture.read_text())
    report = dict(recorded_stamp=payload['recorded_stamp'],
                  recorded_clearance_m=payload['recorded_clearance_m'],
                  independent_minimum_clearance_m=payload['independent_minimum_clearance_m'],
                  attitude_sampling_error_s=payload['attitude_sampling_error_s'],
                  routes=[route(kind, payload) for kind in (LocalPlanner, FastConnectedPlanner)])
    print(json.dumps(report, indent=2), flush=True)
    for item in report['routes']:
        assert abs(item['origin_clearance_m']-payload['recorded_clearance_m']) < .005, (
            'Registration approximation does not reproduce the recorded clearance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    if args.build:
        build()
    replay()
