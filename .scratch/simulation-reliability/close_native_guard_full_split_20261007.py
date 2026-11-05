"""Verify full native split evidence without adopting the isolated controller."""
import hashlib, json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = root / 'logs/reliability_render_split_guard_full_s20261003_20261007'
snapshot = root / '.scratch/native_disturbance_guard_candidate_20261007'
focused = root / 'logs/reliability_render_split_return_disturbance_guard_20261007'
read = lambda path: json.loads(path.read_text())
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
summary, grade = read(out / 'summary.json'), read(out / 'grade.json')
assert summary['final_armed'] is False
for name, sha in read(out / 'source_manifest.json').items():
    path = Path(name) if Path(name).is_absolute() else snapshot / name
    assert digest(path) == sha, name
for name, sha in read(out / 'runtime_configuration_manifest.json')['sha256'].items():
    assert digest(out / name) == sha, name
for name in ('decision_inputs.json', 'decision_inputs_navigation.json'):
    audit = read(out / name)
    assert audit['pass'] and not audit['missing_nodes'] and not audit['forbidden_subscriptions']
    assert {'velocity_controller_capture_driver', 'velocity_controller_clock_driver'} <= audit['nodes'].keys()
assert read(out / 'owned_node_import_resolution_20261007.json')['all_match_frozen']
archive = read(focused / 'candidate_archive_review_20261007.json')
assert digest(focused / 'frozen_candidate_source.zip') == archive['archive_sha256']
review = dict(scope='Full rendered split course, normal startup and calibrated delivery',
              summary=summary, checks_passed=sum(v is True for v in grade['checks'].values()),
              checks_total=len(grade['checks']), source_verified=True, runtime_verified=True,
              input_audits_verified=True, owned_imports_verified=True,
              source_archive=str(focused / 'frozen_candidate_source.zip'),
              archive_sha256=archive['archive_sha256'], accepted_source=False,
              limitation='Isolated guard; coupled gust cases still contact. Other courses and final source are unqualified.')
with (out / 'closed_full_review_20261007.json').open('x') as stream:
    json.dump(review, stream, indent=2)
print(json.dumps(review, indent=2))
