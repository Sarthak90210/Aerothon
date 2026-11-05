"""Read-only independent trace and archived-baseline review; no ROS imports."""
import hashlib
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.scratch/simulation-reliability/coupled_snapshot_independent_review_20261006.json'


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def event(row):
    if row is None:
        return None
    d = row['detail']
    return dict(stamp=row['stamp'], independent_preintegration_clearance_m=row['independent_clearance_m'],
                pose=row['pose'], observed_clearance_m=d.get('observed_clearance_m'),
                command_body_mps=[d.get('cmd_vx'), d.get('cmd_vy_left')],
                braking_clearance_available=d.get('braking_clearance_available'),
                ground_velocity_world_mps=d.get('ground_velocity_world_mps'),
                disturbance_world_mps=d.get('disturbance_world_mps'),
                fcu_velocity_age_s=d.get('fcu_velocity_age_s'), scan_age_s=d.get('scan_age_s'),
                state=d.get('state'), reason=d.get('recovery_reason'))


diagnostics = read(ROOT / 'logs/reliability_remaining_qualification_20261006/report.json')
trials = []
for trial in diagnostics['gust_diagnostics']:
    data = read(ROOT / trial['output'])
    rows = data['rows']
    first = lambda pred: next((r for r in rows if pred(r)), None)
    match = re.search(r't=([\d.]+)s', data.get('failure') or '')
    trials.append(dict(seed=trial['seed'], kind=trial['kind'], passed=data['passed'],
        command_delay_s=data['command_delay_s'], source_sha256=data['source_sha256'],
        records=len(rows), minimum_logged_preintegration_clearance_m=min(r['independent_clearance_m'] for r in rows),
        contact_failure_s=float(match[1]) if match else None,
        first_physical_clearance_violation=event(first(lambda r:r['independent_clearance_m'] < .7)),
        first_uncertified_raw_zero=event(first(lambda r:r['detail'].get('braking_clearance_available') is False
            and r['detail'].get('cmd_vx') == 0 and r['detail'].get('cmd_vy_left') == 0)),
        output=trial['output']))

independent = read(ROOT / 'logs/reliability_independent_gust_envelope_baseline_20261006.json')
baseline = read(ROOT / diagnostics['gust_diagnostics'][0]['output'])
reproduction = dict(rows_identical=independent['rows'] == baseline['rows'],
                    failure_identical=independent['failure'] == baseline['failure'],
                    source_sha256_identical=independent['source_sha256'] == baseline['source_sha256'])

names = ['reliability_render_my_world_s20261003_handover_guard_20261006',
         'reliability_render_my_world_s1001_handover_guard_20261006']
source_manifests = [read(ROOT / 'logs' / n / 'source_manifest.json') for n in names]
archive_reviews = []
frozen_manifests = []
for name in names:
    run = ROOT / 'logs' / name
    expected = read(run / 'source_archive_verification.json')
    archive_path = run / expected['archive']
    archive_hash = sha(archive_path.read_bytes())
    failures = []
    with zipfile.ZipFile(archive_path) as z:
        frozen = json.loads(z.read('archive_manifest.json'))
        for relative, digest in frozen.items():
            if sha(z.read('source/' + relative)) != digest:
                failures.append(relative)
        for relative, digest in source_manifests[len(frozen_manifests)].items():
            if relative.startswith('src/') and frozen.get(relative) != digest:
                failures.append('source manifest mismatch: ' + relative)
    frozen_manifests.append(frozen)
    archive_reviews.append(dict(run=name, archive_sha256=archive_hash,
        archive_sha256_matches=archive_hash == expected['archive_sha256'],
        source_entries_checked=len(frozen), byte_hash_failures=failures))

snapshot = ROOT / '.scratch/qualified_navigation_baseline_20261006'
snapshot_review = dict(path=str(snapshot), exists=snapshot.exists())
if snapshot.exists():
    missing, mismatched, symlinked = [], [], []
    for relative, digest in frozen_manifests[0].items():
        path = snapshot / relative
        if not path.is_file():
            missing.append(relative)
        elif sha(path.read_bytes()) != digest:
            mismatched.append(relative)
        if path.is_symlink():
            symlinked.append(relative)
    snapshot_review.update(source_entries_checked=len(frozen_manifests[0]), missing=missing,
        mismatched=mismatched, symlinked=symlinked,
        core_matches_both_qualified_runs=all((snapshot / relative).is_file()
            and sha((snapshot / relative).read_bytes()) == digest
            for manifest in source_manifests for relative,digest in manifest.items()
            if relative.startswith('src/')))
    for name in ('snapshot_verification.json', 'decision_import_verification.json'):
        path = snapshot / name
        snapshot_review[name] = read(path) if path.is_file() else None
    imports = snapshot_review['decision_import_verification.json']
    if imports:
        failures = []
        for name, evidence in imports.items():
            path = Path(evidence['path']).resolve()
            if not path.is_relative_to(snapshot.resolve()):
                failures.append(name + ': outside snapshot')
                continue
            relative = str(path.relative_to(snapshot.resolve()))
            if evidence['sha256'] != frozen_manifests[0].get(relative):
                failures.append(name + ': audit hash differs from archived entry')
            if sha(path.read_bytes()) != evidence['sha256']:
                failures.append(name + ': bytes changed since import audit')
        snapshot_review['runtime_import_audit'] = dict(modules_checked=len(imports), failures=failures)
    assets_path = snapshot / 'additional_assets_manifest.json'
    if assets_path.is_file():
        asset_manifest = read(assets_path)
        failures = []
        inherited = []
        for relative, digest in asset_manifest['sha256'].items():
            path = snapshot / relative
            if not path.is_file() or sha(path.read_bytes()) != digest:
                failures.append(relative)
            if frozen_manifests[0].get(relative) == digest:
                inherited.append(relative)
        snapshot_review['additional_assets'] = dict(provenance=asset_manifest['provenance'],
            entries_checked=len(asset_manifest['sha256']), failures=failures,
            already_present_in_qualified_archive=inherited,
            unarchived_entries=len(asset_manifest['sha256'])-len(inherited))

report = dict(qualification_pair=read(ROOT / 'logs/reliability_standard_pair_handover_guard_20261006.json'),
    all_combined_disturbance_trials_failed=all(not t['passed'] for t in trials),
    trials=trials, independent_reproduction=reproduction,
    qualified_source_manifests_identical=source_manifests[0] == source_manifests[1],
    qualified_archive_manifests_identical=frozen_manifests[0] == frozen_manifests[1],
    archives=archive_reviews, snapshot=snapshot_review,
    limits=['Recorded minimum is pre-integration and excludes the final contact integration step.',
            'This review does not qualify headless rendered perception or delivery.',
            'Finite seed failures are control failures on feasible geometry, not proof of dynamic impossibility.',
            'Gaussian OU turbulence has no deterministic configured disturbance/derivative maximum.'])
OUT.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(report=str(OUT), trials=len(trials), all_failed=report['all_combined_disturbance_trials_failed'],
    reproduction=reproduction, archives=archive_reviews,
    snapshot={k:v for k,v in snapshot_review.items() if k not in ('snapshot_verification.json','decision_import_verification.json')}),indent=2))
