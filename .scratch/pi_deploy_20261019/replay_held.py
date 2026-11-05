"""Replay the actual deployed matcher locally against captured LiDAR; never connects to ROS."""
import collections
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
module=ROOT/'src/aerothon_mission/mission_bringup/mission_bringup/lidar_odometry.py'
spec=importlib.util.spec_from_file_location('deployed_lidar_odometry',module)
matcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(matcher)
rows=[json.loads(x) for x in (HERE/'held_observation.jsonl').read_text().splitlines() if x.startswith('{')]
scans=[s for s in rows if s['kind']=='scan']
mounts={t['child']:t for s in rows if s['kind']=='tf_static' for t in s['transforms']}

def points(s):
    ranges=np.array([np.nan if r is None else r for r in s['ranges']])
    valid=np.isfinite(ranges)&(ranges>max(.15,s['range_min']))&(ranges<min(12.,s['range_max']))
    angle=s['angle_min']+np.flatnonzero(valid)*s['angle_increment']
    cloud=np.c_[np.cos(angle)*ranges[valid],np.sin(angle)*ranges[valid],np.zeros(valid.sum())]
    t=mounts[s['frame']]
    assert t['parent']=='base_link', 'Need the exact direct mount, not a composed approximation'
    return (cloud@Rotation.from_quat(t['rotation']).as_matrix().T+np.array(t['translation']))[:,:2]

def first_iteration(reference,current,initial=(0,0,0)):
    tree=cKDTree(reference)
    _,neighbours=tree.query(reference,k=7)
    local=reference[neighbours]
    centred=local-local.mean(axis=1,keepdims=True)
    values=np.linalg.eigvalsh(np.einsum('nki,nkj->nij',centred,centred))
    line=values[:,0]<.15*np.maximum(values[:,1],1e-9)
    moved=matcher.transform(current,np.asarray(initial))
    distance,nearest=tree.query(moved)
    near=distance<.35
    valid=near&line[nearest]
    return dict(reference_returns=len(reference),current_returns=len(current),
        reference_line_fraction=float(line.mean()),close_fraction=float(near.mean()),
        matched_line_count=int(valid.sum()),matched_line_fraction=float(valid.mean()))

clouds=[points(s) for s in scans]
self_results=[]
for i,cloud in enumerate(clouds):
    result=dict(index=i,stamp=scans[i]['stamp'],**first_iteration(cloud,cloud))
    try:
        pose,q=matcher.match_scan(cloud,cloud)
        result.update(state='Tracking',quality=q)
    except ValueError as e: result.update(state='Held',reason=str(e))
    self_results.append(result)

pair_results=[]
for i in range(1,len(clouds)):
    result=dict(index=i,stamp=scans[i]['stamp'],**first_iteration(clouds[i-1],clouds[i]))
    try:
        pose,q=matcher.match_scan(clouds[i-1],clouds[i])
        result.update(state='Tracking',pose=pose.tolist(),quality=q)
    except ValueError as e: result.update(state='Held',reason=str(e))
    pair_results.append(result)

actual_match=matcher.match_scan
last_match={}
def observed_match(*args, **kwargs):
    last_match.clear()
    pose,quality=actual_match(*args, **kwargs)
    last_match.update(pose=pose.tolist(), quality=quality)
    return pose,quality
matcher.match_scan=observed_match
engine=matcher.ScanOdometry()
reference_index=None
replay=[]
for i,(scan,cloud) in enumerate(zip(scans,clouds)):
    result=dict(index=i,stamp=scan['stamp'])
    if engine.reference is not None:
        result.update(first_iteration(engine.reference,cloud,engine.relative))
        result['last_success_age_s']=scan['stamp']-engine.stamp
        result['reference_index']=reference_index
    previous_reference=engine.reference
    last_match.clear()
    try:
        pose,q=engine.update(cloud,scan['stamp'])
        result.update(state='Tracking',pose=pose.tolist(),quality=q)
    except ValueError as e: result.update(state='Held',reason=str(e))
    if last_match: result['raw_match']=last_match.copy()
    if previous_reference is not engine.reference: reference_index=i
    replay.append(result)

def counts(results):
    return dict(collections.Counter(r['state']+': '+r.get('reason','') for r in results))
out=dict(source='actual deployed matcher and captured live scans',
    self_match=counts(self_results),adjacent_match=counts(pair_results),fresh_origin_replay=counts(replay),
    self_match_line_fraction_percentiles=np.percentile([s['reference_line_fraction'] for s in self_results],[0,50,100]).tolist(),
    self_results=self_results,pair_results=pair_results,replay=replay)
(HERE/'held_replay.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ['self_results','pair_results','replay']},indent=2))
print(json.dumps({'first_self':self_results[0],'first_pair':pair_results[0],'first_replay':replay[:3]},indent=2))
if '--assert-tracking' in sys.argv:
    assert all(r['state']=='Tracking' for r in replay), 'Captured live scans reproduce mapping holds in the deployed matcher'
if '--assert-recovery' in sys.argv:
    accepted=[r['index'] for r in replay if r['state']=='Tracking']
    last_accepted=accepted[-1]
    still_matchable=sum(r['state']=='Tracking' and r['index']>last_accepted for r in pair_results)
    persistent_hold=replay[-1]['state']=='Held' and replay[-1].get('last_success_age_s',0)>10
    assert not (persistent_hold and still_matchable>20), (
        f"Initialized, then held for {replay[-1]['last_success_age_s']:.2f}s while "
        f"{still_matchable} subsequent adjacent scan pairs still align")
