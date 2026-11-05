"""Export actual external-camera captures on their simulation timeline."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--preview-only', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
capture = root / '.scratch/birdseye_split_v38_20261009_retry3'
mission = root / 'logs/user_birdseye_split_v38_s20261003_retry3_20261009'
def read(path):
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows
frames = read(capture/'frames.jsonl')
onboard = read(mission/'onboard.jsonl')
truth = read(mission/'evaluation_vehicle_truth.jsonl')
truth_times = [row['stamp'] for row in truth]
onboard_times = [row['stamp'] for row in onboard]
armed = [row for row in onboard if row.get('flight',{}).get('data',{}).get('armed')]
assert armed, 'Mission has not armed yet'
first_arm = armed[0]['stamp']
disarmed = [row for row in onboard if row['stamp']>first_arm and
    row.get('flight',{}).get('data',{}).get('connected') and
    row.get('flight',{}).get('data',{}).get('armed') is False]
if not args.preview_only:
    assert disarmed, 'Recording cannot be delivered before actual disarm'
    assert (mission/'recorded_result.json').exists()
disarm = disarmed[0]['stamp'] if disarmed else None
selected = [frame for frame in frames if frame['stamp']>=first_arm-4]
assert selected
out = mission/'birds_eye_view'
out.mkdir(exist_ok=True)
rendered = out/'frames'
if not args.preview_only:
    rendered.mkdir(exist_ok=False)
focal = 1600/(2*math.tan(.84/2))
def overlay(frame):
    image = cv2.imread(str(capture/frame['file']))
    assert image is not None
    plain = image.copy()
    now = frame['stamp']
    i = max(0,bisect.bisect_right(onboard_times,now)-1)
    row = onboard[i]
    raw_state = row.get('mission','STARTUP')
    labels = dict(WAITING='Ready', PREFLIGHT='Preflight', TAKEOFF='Takeoff',
        START_QR='Read start marker', CAMERA_NADIR='Camera adjustment',
        CAMERA_FWD='Camera adjustment', CAMERA_BANNER='Find banner',
        BANNER_ALIGN='Align with gate', GATE_CROSSING='Cross gate',
        CORRIDOR_NAV='Outbound corridor', ENTER_ZONE='Enter delivery field',
        SEARCH_QR='Find delivery target', CENTER_TARGET='Center over target',
        WINCH_DROP='Deliver payload', RETURN_TRANSIT='Return transit',
        RETURN_GATE_SEARCH='Find return gate', RETURN_CORRIDOR='Return corridor',
        RETURN='Return home', LAND='Landing', DONE='Complete', FAILED='Mission stopped',
        ABORT='Safe landing')
    state = labels.get(raw_state,raw_state.replace('_',' ').title())
    flight = row.get('flight',{}).get('data',{})
    title = f"SPLIT CORRIDORS   |   BIRD'S-EYE VIEW   |   {max(0,now-first_arm):05.1f} s   |   {state}"
    if disarm is not None and now>=disarm:
        title += '   |   DISARMED'
    cv2.rectangle(image,(0,0),(1600,42),(23,27,31),-1)
    cv2.putText(image,title,(22,29),cv2.FONT_HERSHEY_SIMPLEX,.72,(235,239,243),2,cv2.LINE_AA)
    index = bisect.bisect_right(truth_times,now)-1
    if index>=0:
        pose = truth[index]
        depth = 90-pose['z']
        u = 800+(pose['x']-24.25)*focal/depth
        v = 600-(pose['y']+4.8)*focal/depth
        if 0<=u<1600 and 42<=v<1200:
            point = (round(u),round(v))
            cv2.circle(image,point,17,(0,217,255),2,cv2.LINE_AA)
            # Magnify the same overhead frame so the aircraft remains visible.
            crop = cv2.getRectSubPix(plain,(144,108),(float(u),float(v)))
            detail = cv2.resize(crop,(336,252),interpolation=cv2.INTER_CUBIC)
            image[87:339,24:360] = detail
            cv2.rectangle(image,(23,86),(360,339),(0,217,255),2)
            cv2.rectangle(image,(24,57),(360,85),(23,27,31),-1)
            cv2.putText(image,'AIRCRAFT DETAIL',(36,77),cv2.FONT_HERSHEY_SIMPLEX,.5,(235,239,243),1,cv2.LINE_AA)
            cv2.putText(image,f"Height {pose['z']:.1f} m   {flight.get('mode','')}",(25,364),
                        cv2.FONT_HERSHEY_SIMPLEX,.5,(32,38,44),1,cv2.LINE_AA)
    return image
if args.preview_only:
    frame = selected[-1]
    cv2.imwrite(str(out/'preview.png'),overlay(frame))
    print(json.dumps(dict(preview=str(out/'preview.png'),stamp=frame['stamp'])))
else:
    manifest = []
    for index,frame in enumerate(selected):
        name = f'frame_{index:06d}.jpg'
        assert cv2.imwrite(str(rendered/name),overlay(frame),[cv2.IMWRITE_JPEG_QUALITY,92])
        manifest.append(dict(file='frames/'+name,stamp=frame['stamp']))
    duration = selected[-1]['stamp']-selected[0]['stamp']+1/3
    with (out/'timeline.ffconcat').open('w',newline='\n') as stream:
        stream.write('ffconcat version 1.0\n')
        for index,frame in enumerate(manifest):
            span = manifest[index+1]['stamp']-frame['stamp'] if index+1<len(manifest) else 1/3
            assert span>0
            stream.write(f"file '{frame['file']}'\nduration {span:.9f}\n")
        stream.write(f"file '{manifest[-1]['file']}'\n")
    (out/'export_metadata.json').write_text(json.dumps(dict(
        origin='Actual passive Gazebo overhead camera captures from a fresh V38 flight; not a reconstructed trajectory',
        world='split_corridors.json',seed=20261003,conditions='calm',qualification_status='paused',
        camera_configuration=json.loads((capture/'configuration.json').read_text()),
        overlays='Elapsed time, observed mission state, aircraft-position highlight and crop from the same overhead frame',
        first_capture_stamp=selected[0]['stamp'],last_capture_stamp=selected[-1]['stamp'],
        first_armed_stamp=first_arm,first_connected_disarm_stamp=disarm,
        duration_s=duration,frames=len(selected),maximum_gap_s=max(b['stamp']-a['stamp'] for a,b in zip(selected,selected[1:])),
        capture_summary=json.loads((capture/'capture_summary.json').read_text()),
        source_archive_sha256=json.loads((root/'logs/reliability_reduced_scope_v38_source_20261008/provenance.json').read_text())['archive_sha256'],
        world_spec_sha256=hashlib.sha256((mission/'world_spec.json').read_bytes()).hexdigest()),indent=2))
    cv2.imwrite(str(out/'preview.png'),overlay(selected[len(selected)//2]))
    print(json.dumps(dict(output=str(out),duration_s=duration,frames=len(selected),actual_disarm=disarm)))
