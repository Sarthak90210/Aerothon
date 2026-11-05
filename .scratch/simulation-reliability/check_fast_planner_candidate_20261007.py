"""Actual captured scans: timing and full segment clearance, plus regressions."""
import hashlib,json,math,sys,time
import argparse
from pathlib import Path
import numpy as np
from sensor_msgs.msg import LaserScan
from types import SimpleNamespace
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from avoidance.velocity_controller import VelocityController
import avoidance.local_planner as module
from fast_connected_planner_candidate_20261007 import FastConnectedPlanner

run=root/'logs/reliability_braked_navigation_candidate_restore_config_20261007/my_world_calm_s1'
scans=[]
for line in (run/'onboard_lidar.jsonl').read_text().splitlines():
    row=json.loads(line);d=row['data'];h=d['header']['stamp']
    stamp=h['sec']+h['nanosec']*1e-9
    if 766.<stamp<771. and (not scans or stamp-scans[-1][0]>.39):
        scans.append((stamp,d))
assert len(scans)>=8
conditioning=SimpleNamespace(_g=lambda key:dict(range_min_valid=.15,range_max_valid=12.,
    mask_sectors_deg=[150.,210.],median_window=3)[key])
results=[]
for stamp,data in scans:
    assert data['header']['frame_id']=='base_link'
    scan=LaserScan();scan.angle_min=data['angle_min'];scan.angle_increment=data['angle_increment']
    scan.ranges=[math.inf if value is None else float(value) for value in data['ranges']]
    bearings,ranges=VelocityController.conditioned(conditioning,scan)
    for axis in (0.,.4,-.4):
        item=dict(capture_stamp=stamp,axis_bearing=axis)
        for label,cls in (('original',module.LocalPlanner),('compiled',FastConnectedPlanner)):
            planner=cls(occupied_radius=.4);planner.observe(bearings,ranges)
            before=time.perf_counter();path=planner.plan(axis)
            item[label]=dict(wall_s=time.perf_counter()-before,path=path,
                segments_certified=all(planner.segment_clear(a,b) for a,b in zip(path,path[1:])),
                reason=planner.reason)
            assert item[label]['segments_certified']
        # The observed-space connectivity requirement must be retained.
        assert bool(item['original']['path'])==bool(item['compiled']['path'])
        results.append(item)
summary=dict(scope='Captured onboard scan performance and segment checks; not flight qualification',
    samples=len(results),original_median_wall_s=float(np.median([r['original']['wall_s'] for r in results])),
    compiled_median_wall_s=float(np.median([r['compiled']['wall_s'] for r in results])),
    original_max_wall_s=max(r['original']['wall_s'] for r in results),
    compiled_max_wall_s=max(r['compiled']['wall_s'] for r in results),
    rows=results,candidate_sha256=hashlib.sha256(Path(__file__).with_name('fast_connected_planner_candidate_20261007.py').read_bytes()).hexdigest())
parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=root/'logs/reliability_fast_planner_captured_scans_20261007.json')
target=parser.parse_args().out
with target.open('x') as handle:json.dump(summary,handle,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
# Run existing behavioral regressions against the candidate class, not copies
# of its implementation. It retains the full existing LocalPlanner interface.
module.LocalPlanner=FastConnectedPlanner
import pytest
raise SystemExit(pytest.main(['-q',str(root/'sim/test_local_planner.py')]))
