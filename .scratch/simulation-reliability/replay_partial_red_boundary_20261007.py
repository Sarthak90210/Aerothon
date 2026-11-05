"""Replay recorded camera images and capture-time FCU pose only."""
import bisect,hashlib,json,math,sys
from pathlib import Path
import cv2,yaml
root=Path(__file__).resolve().parents[2]
for package in ('perception_banner','perception_redzone'):
    sys.path.insert(0,str(root/'src/aerothon_perception'/package))
from perception_redzone.georef import ground_point_q
from partial_red_boundary_candidate_20261007 import CONFIG,partial_boundaries
out=root/'logs/reliability_render_rb_rotated_s20261003_observation_repairs_20261007'
intrinsics=out/'runtime_parameters/11683_launch_params_dl16_imn'
hfov=float(yaml.safe_load(intrinsics.read_text())['/**']['ros__parameters']['camera_hfov'])
rows=[json.loads(line) for line in (out/'onboard.jsonl').open()]
poses=[r['pose']['data'] for r in rows if r.get('pose')]
def stamp(p):return p['header']['stamp']['sec']+p['header']['stamp']['nanosec']*1e-9
# Repeated observer copies do not introduce extra capture-time pose samples.
poses=list({stamp(p):p for p in poses}.values());poses.sort(key=stamp)
times=[stamp(p) for p in poses]
events=[]
for line in (out/'camera_frames.jsonl').open():
    row=json.loads(line); t=row['capture_stamp']
    if not 197<=t<=208:continue
    # Match the detector's nearest capture-time pose policy, restricted to
    # samples captured before the recorded frame receipt. Receipt is a replay
    # proxy; this does not claim the original node had this exact callback order.
    j=bisect.bisect_left(times,t)
    choices=[i for i in (j-1,j) if 0<=i<len(times) and times[i]<=row['recorded_stamp']]
    if not choices:continue
    i=min(choices,key=lambda i:abs(times[i]-t));p=poses[i]['pose']
    if abs(t-times[i])>.2:continue
    xyz=p['position'];q=p['orientation']
    def project(contour,wh):
        poly=[]
        for u,v in cv2.approxPolyDP(contour,2,True).reshape(-1,2):
            point=ground_point_q(float(u),float(v),wh,hfov,xyz['z'],
                (xyz['x'],xyz['y']),(q['w'],q['x'],q['y'],q['z']),math.pi/2)
            if point is None:return []
            poly.append(point)
        return poly
    path=out/'exported_camera_frames'/f"frame_{row['index']+1:08d}.png"
    frame=cv2.imread(str(path));assert frame is not None
    boundaries=partial_boundaries(frame,xyz['z'],hfov,project)
    events.append(dict(capture_stamp=t,recorded_stamp=row['recorded_stamp'],
        image=str(path.relative_to(root)),pose_stamp=times[i],boundaries=boundaries))
result=dict(scope='Camera and FCU pose replay only; calibration evidence, not flight qualification',
    config=CONFIG,hfov_rad=hfov,intrinsics_source=str(intrinsics.relative_to(root)),
    source_sha256=hashlib.sha256(Path(__file__).with_name('partial_red_boundary_candidate_20261007.py').read_bytes()).hexdigest(),
    events=events,first_candidate=next((e for e in events if e['boundaries']),None),
    pose_policy='nearest capture-time sample, at most 0.2 s away; recorded receipt is a replay availability proxy',
    production_modified=False)
target=root/'logs/reliability_partial_red_boundary_replay_intrinsics_20261007.json'
with target.open('x') as handle:json.dump(result,handle,indent=2)
print(json.dumps(dict(frames=len(events),first_candidate=result['first_candidate']),indent=2))
