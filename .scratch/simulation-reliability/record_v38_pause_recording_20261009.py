"""Close the requested recording checkpoint; qualification remains paused."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / '.scratch/simulation-reliability'
relative = 'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
run = root / relative
summary = json.loads((run / 'summary.json').read_text())
grade = json.loads((run / 'grade.json').read_text())
timeline = json.loads((run / 'video_timeline.json').read_text())
assert not summary['final_armed'] and not summary['acceptance_pass']
assert timeline['decode_pass'] and float(timeline['export']['duration']) > 471
manifest = json.loads((root / '.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
assert all(hashlib.sha256((root / name).read_bytes()).hexdigest() == sha for name, sha in manifest.items())
videos = {name: dict(bytes=(run/name).stat().st_size, sha256=hashlib.sha256((run/name).read_bytes()).hexdigest())
          for name in ['onboard.mp4', 'onboard_sim_time.mp4']}
receipt = dict(qualification_status='paused by user', recording_request_world='split_corridors.json',
    run=relative, source_unchanged=True, video_timeline=timeline, videos=videos,
    acceptance_pass=False, checks_passed=sum(grade['checks'].values()), checks_required=len(grade['checks']),
    actual_disarm_confirmed=True, preserved_failures=summary['failures'],
    delivery_confirmed=summary['mission_result']['delivery_confirmed'])
(run / 'user_recording_delivery_checkpoint.json').write_text(json.dumps(receipt, indent=2))
note = ('## Qualification paused by user; custom-world recording supplied\n\n'
        'Current V38 split_corridors.json, calm seed 20261003 completed recording\n'
        'through actual disarm. Video decode passed; simulation-time export\n'
        'duration is 471.201 seconds. Delivery was confirmed. The run FAILED\n'
        '17/22 acceptance checks: return became STUCK and independent clearance\n'
        'fell to 0.6949338146612648 m, below unchanged 0.70 m. Safe operator RTL\n'
        'returned home and disarmed; associated mode, ceiling and incomplete\n'
        'return checks remain failed. Original records and stop receipt retained.\n'
        'No remaining native runs or campaign were started. Source is unaccepted.\n'
        'Record: ' + relative + '/user_recording_delivery_checkpoint.json\n\n')
for name in ['status.md', 'evidence_report_20261007.md']:
    path = base / name
    text = path.read_text(encoding='utf-8')
    if not text.startswith('## Qualification paused by user;'):
        path.write_text(note + text, encoding='utf-8')
path = base / 'evidence_index_20261007.json'
index = json.loads(path.read_text(encoding='utf-8'))
index['active_runs'] = []
index['active_trial'] = None
index['verification']['v38_native_split_recording_checkpoint'] = relative + '/user_recording_delivery_checkpoint.json'
index['current_continuation']['status'] = 'paused by user'
index['current_continuation']['remaining'] = 'Resolve recorded native split return failure; qualification paused. Other four native runs and 96-flight campaign unstarted.'
path.write_text(json.dumps(index, indent=2), encoding='utf-8')
print(json.dumps({key: receipt[key] for key in ['qualification_status', 'checks_passed', 'checks_required', 'source_unchanged', 'actual_disarm_confirmed']}))
