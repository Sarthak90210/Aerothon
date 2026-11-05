"""Matched physical controls; preserve every failed diagnostic case."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
captures = (
    'logs/reliability_gust_dirty_empirical_viability_retry1_20261007.json',
    'logs/reliability_gust_dirty_calm_empirical_viability_20261007.json',
    'logs/reliability_gust_dirty_calm_empirical_path_reserve_20261007.json',
    'logs/reliability_gust_dirty_calm_empirical_profile_reserve_20261007.json',
    'logs/reliability_gust_late_calm_empirical_profile_reserve_20261007.json',
    'logs/reliability_gust_late_calm_baseline_20261007.json',
    'logs/reliability_gust_dirty_calm_baseline_20261007.json',
)
rows = []
for capture in captures:
    path = root/capture
    data = json.loads(path.read_text())
    minimum = data['minimum_actual_clearance_m']
    record = dict(
        capture=capture, capture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        policy=data['diagnostic_policy'], kind=data['kind'], seed=data['seed'],
        wind_profile=data['diagnostic_wind_profile'],
        command_delay_s=data['command_delay_s'], response_s=.6,
        source_hashes=data['source_sha256'],
        physical_command_basis=data['physical_command_basis'],
        fixture_traversal_passed=data['passed'],
        actual_minimum_surface_clearance_m=minimum,
        last_recorded_command_stamp_s=data['rows'][-1]['stamp'],
        records=len(data['rows']), failure=data['failure'],
        source_files_still_match=all(
            hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
            for name,sha in data['source_sha256'].items()),
        classification=('PHYSICAL_FIXTURE_TRAVERSAL_PASS' if data['passed'] else
            'PHYSICAL_CLEARANCE_FAILURE' if minimum is not None and minimum<.7 else
            'SAFE_FINITE_HORIZON_TRAVERSAL_FAILURE'),
    )
    assert data['command_delay_s']==.4
    assert record['source_files_still_match']
    rows.append(record)
timeline = json.loads((root/'.scratch/simulation-reliability/empirical_hold_release_receipt_timeline_20261007.json').read_text())
archive = root/'.scratch/simulation-reliability/empirical_profile_reserve_sources_20261007.zip'
result = dict(
    scope='Offline physical fixture diagnostics only; no rendered perception or hardware qualification',
    accepted_for_production=False,
    conclusion='Reserve/latch/profile policy rejects an already passing dirty still-air case; no default-gust traversal repaired.',
    supported_original_cases='Only the two tested still-air cases: dirty seed0 and .15 s late-scan seed1, both with actual .4 s queued body/yaw commands and .6 s actuator response.',
    hold_release_causal_finding=dict(
        completed_episodes=timeline['completed_travel_episodes'],
        relatches_before_first_receipt=timeline['relatches_before_first_receipt'],
        note='Queued forward packets still arrive after relatch; subsequent measured-position corrections undo brief travel. This occurred in four episodes, not all travel episodes.',
        timeline='.scratch/simulation-reliability/empirical_hold_release_receipt_timeline_20261007.json'),
    prediction_bound_limitation='Historical forecast errors and raw residual derivatives are empirical observations, not guaranteed future disturbance bounds. Finite safe holds do not establish a general gust envelope.',
    archive=str(archive.relative_to(root)), archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), cases=rows,
)
out = root/'.scratch/simulation-reliability/empirical_reserve_matched_control_comparison_20261007.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(dict(accepted_for_production=False, cases=[{
    key:value for key,value in case.items() if key in (
        'capture','policy','classification','actual_minimum_surface_clearance_m',
        'last_recorded_command_stamp_s','source_files_still_match')}
    for case in rows])))
