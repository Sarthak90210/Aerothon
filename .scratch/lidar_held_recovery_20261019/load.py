import importlib.util, json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2]
EV=ROOT/'.scratch/pi_deploy_20261019/held_observation.jsonl'
def load_module(path=ROOT/'src/aerothon_mission/mission_bringup/mission_bringup/lidar_odometry.py', name='lo'):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
rows=[json.loads(x) for x in EV.read_text().splitlines() if x.startswith('{')]
scans=[s for s in rows if s['kind']=='scan']
mounts={t['child']:t for s in rows if s['kind']=='tf_static' for t in s['transforms']}
def points(s):
    ranges=np.array([np.nan if r is None else r for r in s['ranges']])
    valid=np.isfinite(ranges)&(ranges>max(.15,s['range_min']))&(ranges<min(12.,s['range_max']))
    angle=s['angle_min']+np.flatnonzero(valid)*s['angle_increment']
    cloud=np.c_[np.cos(angle)*ranges[valid],np.sin(angle)*ranges[valid],np.zeros(valid.sum())]
    t=mounts[s['frame']]
    return (cloud@Rotation.from_quat(t['rotation']).as_matrix().T+np.array(t['translation']))[:,:2]
clouds=[points(s) for s in scans]
stamps=[s['stamp'] for s in scans]
