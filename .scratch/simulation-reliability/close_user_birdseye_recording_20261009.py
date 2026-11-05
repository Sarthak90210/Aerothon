"""Deliver a verified user-requested recording while qualification stays paused."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
relative = 'logs/user_birdseye_split_v38_s20261003_retry3_20261009'
run = root/relative
metadata = json.loads((run/'birds_eye_view/export_metadata.json').read_text())
summary = json.loads((run/'summary.json').read_text())
grade = json.loads((run/'grade.json').read_text())
assert metadata['last_capture_stamp']>metadata['first_connected_disarm_stamp']
assert metadata['capture_summary']['dropped']==0
assert not summary['final_armed']
manifest = json.loads((root/'.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
videos = {}
for name,ratio in [('birds_eye',1),('birds_eye_4x',4)]:
    path = run/(name+'.mp4')
    probe = json.loads((run/(name+'_video_probe.json')).read_text())['streams'][0]
    assert path.stat().st_size>100000 and probe['width']==1600 and probe['height']==1200
    assert abs(float(probe['duration'])-metadata['duration_s']/ratio)<.25
    assert (run/(name+'_decode.log')).read_text().strip()==''
    videos[path.name] = dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            video=probe,decode_pass=True,playback_speed=ratio)
record = dict(request='Bird-eye view of current code on split_corridors.json',
    qualification_status='paused by user',source_unchanged=True,source_files=len(manifest),
    controller_source_archive_sha256=metadata['source_archive_sha256'],
    recording=metadata,videos=videos,mission_result=summary['mission_result'],
    recorded_acceptance_checks=dict(passed=sum(grade['checks'].values()),required=len(grade['checks']),failures=summary['failures']),
    qualification_scope='User-requested recording with an added passive overhead camera and a private provenance adapter. The previous failed V38 qualification trial remains failed; no qualification resume or completion is claimed.',
    retained_setup_failures=[dict(attempt=1,reason='Private launcher CRLF formatting; no flight started'),
                             dict(attempt=2,reason='Original provenance collector correctly rejected private launcher identity; no flight started')],
    cleanup_stderr='vehicle_contact_recorder.log retains a native pybind11 GIL shutdown abort after actual disarm',
    native_run=relative)
(run/'birds_eye_recording_closed_review.json').write_text(json.dumps(record,indent=2))
base = root/'.scratch/simulation-reliability'
index_path=base/'evidence_index_20261007.json'
index=json.loads(index_path.read_text(encoding='utf-8'))
index['verification']['user_birdseye_recording_20261009']=relative+'/birds_eye_recording_closed_review.json'
index['active_runs']=[]
index['active_trial']=None
index['current_continuation']['status']='paused by user'
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
note=('## User-requested bird-eye recording, qualification still paused\n\n'
      'A fresh V38 split_corridors.json calm seed 20261003 run was recorded\n'
      'with an added passive native overhead camera. The flight completed\n'
      'delivery, full return traversal and actual disarm. Its own grader\n'
      'reports 22/22, while the previous V38 qualification run remains\n'
      '17/22 FAILED. Different observation configuration and a private\n'
      'provenance adapter are documented; this demonstration is not used\n'
      'to resume or complete qualification. Both records remain preserved.\n'
      'The overhead capture contains 1501 frames with zero drops; the\n'
      'export contains 1340 frames at original capture intervals, 446.22\n'
      'seconds, including confirmed disarm. Full-speed and 4x MP4 exports\n'
      'decode successfully. Source hashes verify all 949 files unchanged.\n'
      'The post-disarm native contact-recorder GIL shutdown abort remains\n'
      'preserved and unresolved. Two unarmed setup attempts are retained.\n'
      'Closed recording proof: '+relative+'/birds_eye_recording_closed_review.json\n\n')
for name in ['status.md','evidence_report_20261007.md']:
    path=base/name
    text=path.read_text(encoding='utf-8')
    if not text.startswith('## User-requested bird-eye recording,'):
        path.write_text(note+text,encoding='utf-8')
print(json.dumps(dict(videos=videos,qualification_status='paused',source_unchanged=True)))
