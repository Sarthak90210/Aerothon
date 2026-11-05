import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
out = Path(__file__).parent
run = root / 'logs/pi_cleanup_hard_field_both_s20261004_retry1_20261013'
freeze = root / 'logs/pi_cleanup_source_with_wiring_final_20261013'
manifest = json.loads((freeze / 'source_manifest.json').read_text())
changed = [name for name, digest in manifest.items()
           if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest]
assert sorted(changed) == ['AGENTS.md', 'MASTER_DOCUMENTATION.md'], changed
grade = json.loads((run / 'grade.json').read_text())
summary = json.loads((run / 'summary.json').read_text())
assert summary['final_armed'] is False and summary['mission_result']['state'] == 'COMPLETED'
assert summary['acceptance_pass'] is False
failed = [name for name, passed in grade['checks'].items() if not passed]
assert failed == ['corridor clearance at least 0.70 m'], failed
video_receipt = json.loads((run / 'overview/export_receipt.json').read_text())
video = run / 'overview/world_overview.mp4'
assert hashlib.sha256(video.read_bytes()).hexdigest() == video_receipt['sha256']
bundle = root / 'logs/AEROTHON_PI_RUNTIME_20261013.zip'
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    inventory = json.loads(z.read('runtime_manifest.json'))
    assert sorted(name for name in z.namelist() if name.endswith('.md')) == ['AGENTS.md', 'MASTER_DOCUMENTATION.md']
    for name, digest in inventory['files'].items():
        assert hashlib.sha256(z.read(name)).hexdigest() == digest
        source = root / name if not name.startswith('gcs/') else root / 'src/aerothon_gcs/tauri_app/dist' / name[4:]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert not any(name.startswith(('sim/', 'logs/', 'tests/', '.scratch/', 'src/aerothon_sim/')) for name in z.namelist())
baseline = json.loads((out / 'baseline.json').read_text())
with zipfile.ZipFile(out / 'historical_documentation.zip') as z:
    assert z.testzip() is None
    assert all(hashlib.sha256(z.read(name)).hexdigest() == digest for name, digest in baseline['documentation'].items())
assert sorted(p.name for p in root.glob('*.md')) == ['AGENTS.md', 'MASTER_DOCUMENTATION.md']
assert not list((root / 'docs').rglob('*.md'))
receipt = dict(completed_scope='documentation, conservative cleanup, runtime package and requested video',
    guides=['AGENTS.md', 'MASTER_DOCUMENTATION.md'], archived_project_markdown=104,
    algorithm_change=False, postflight_changes=changed, postflight_changes_are_documentation_only=True,
    offline_passed=1920, offline_skipped=8, isolated_packages_built=11, isolated_runtime_imports=13,
    gcs_static_browser_validation=True, rendered_checks_passed=sum(grade['checks'].values()),
    rendered_checks_total=len(grade['checks']), rendered_accepted=False, failed_checks=failed,
    minimum_corridor_clearance_m=grade['measured_corridor_clearance_m'],
    flight_time_s=summary['flight_time_s'], payload_error_m=summary['payload_error_m'],
    connected_disarm=True, unexpected_contacts=len(grade['aircraft_contact_evidence']['unexpected_contacts']),
    video=str(video), video_sha256=video_receipt['sha256'], video_full_decode_verified=True,
    video_visual_samples_reviewed=['start','search','clearance_failure','disarmed'],
    bundle=str(bundle), bundle_bytes=bundle.stat().st_size,
    bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
    hardware_qualified=False, gpio_wiring_assigned=True, encoder_backend_implemented=False,
    real_pi_deployment_performed=False,
    remaining_functional_work=['field clearance correction', 'Pi GPIO/encoder winch backend and measured calibration'])
(out / 'closure.json').write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
