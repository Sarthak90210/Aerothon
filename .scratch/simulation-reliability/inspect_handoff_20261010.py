"""Read-only handoff inventory. Does not start simulations or change evidence."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def read(name):
    p = root / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

def emit(label, value):
    print(json.dumps({'label': label, 'value': value}, ensure_ascii=True))

manifest = read('.scratch/reduced_scope_v39_candidate_20261008/source_manifest.json')
mismatches = []
for name, expected in manifest.items():
    p = root / name.replace('\\', '/')
    actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if actual != expected:
        mismatches.append({'path': name, 'expected': expected, 'actual': actual})
archive = root / 'logs/reliability_reduced_scope_v39_source_20261008/frozen_source.zip'
emit('source', {'controlled_files': len(manifest), 'mismatches': mismatches,
                'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
base = 'logs/reliability_reduced_v39_targeted_20261008'
report = read(base + '/report.json')
emit('targeted_header', {k: v for k, v in report.items() if k != 'results'})
for result in report['results']:
    emit('targeted_case', {k: v for k, v in result.items() if not isinstance(v, (list, dict))})
    emit('targeted_case_keys', list(result))
native = 'logs/reliability_reduced_v39_focused_split_s20261003_20261009'
grade = read(native + '/grade.json')
emit('native_grade_keys', list(grade))
contacts = grade['aircraft_contact_evidence']
from collections import Counter
unexpected = contacts['unexpected_contacts']
emit('native_contact', {k: v for k, v in contacts.items() if k != 'unexpected_contacts'})
emit('native_contact_summary', dict(count=len(unexpected),
    pairs=dict(Counter(x['vehicle'] + ' -> ' + x['other'] for x in unexpected)),
    first=unexpected[0] if unexpected else None, last=unexpected[-1] if unexpected else None))
for key in ('checks', 'summary', 'detector_rates', 'detector_metrics', 'recording_metrics'):
    if key in grade:
        emit('native_' + key, grade[key])
for name in ('summary.json', 'recorded_result.json', 'configuration.json', 'video_timeline.json', 'vehicle_contact_ready.json'):
    emit('native_' + name, read(native + '/' + name))
for directory in ('logs/reliability_reduced_scope_v39_source_20261008', base):
    emit('closure_files_' + directory, [str(p.relative_to(root)) for p in (root/directory).glob('*review*.json')])
index = read('.scratch/simulation-reliability/evidence_index_20261007.json')
emit('index_keys', list(index))
for key in ('current_candidate', 'active_runs', 'scope', 'qualification_status', 'current_continuation'):
    if key in index:
        emit('index_' + key, index[key])
emit('v39_log_paths', [str(p.relative_to(root)) for p in (root/'logs').glob('*v39*')])
for version, directory in (
    ('v38_native', 'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'),
    ('v38_birdseye', 'logs/user_birdseye_split_v38_s20261003_retry3_20261009')):
    s = read(directory + '/summary.json')
    emit(version + '_summary', s)
