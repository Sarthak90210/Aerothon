"""Hash closed evidence and preserve every navigation failure, using Windows IO."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_focused_paired_scan_navigation_verified_20261007'
report=json.loads((out/'report.json').read_text())
assert report['finished_wall'] and report['source_unchanged'] and len(report['results'])==10
archive=root/'logs/reliability_paired_scan_navigation_s5_assets_20261007/frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==report['source_archive_sha256']
with zipfile.ZipFile(archive) as source:
    manifest=json.loads(source.read('source_manifest.json'))
    assert all(hashlib.sha256(source.read(name)).hexdigest()==sha for name,sha in manifest.items())
rows=[]
for result in sorted(report['results'],key=lambda row:row['run']):
    path=out/result['run'];grade=json.loads((path/'navigation_grade.json').read_text())
    assert json.loads((path/'source_manifest.json').read_text())==manifest
    assert result['harness_valid'] and result['forecast_recording_closed']
    assert not grade['full_grade']['final_armed']
    assert (path/'track.csv').read_bytes()==(path/'evaluation_truth_track.csv').read_bytes()
    required=['configuration.json','world_spec.json','layout.json','source_manifest.json',
        'onboard.jsonl','onboard_lidar.jsonl','flight_commands.jsonl','winch_commands.jsonl',
        'detector_events.jsonl','evaluation_truth_track.csv','independent_command_receipt_timing.json',
        'navigation_grade.json','run.json','stack.log']
    files={name:dict(bytes=(path/name).stat().st_size,sha256=hashlib.sha256((path/name).read_bytes()).hexdigest()) for name in required}
    forecast=out/f"{result['run']}_forecasts.json"
    rows.append(dict(run=result['run'],navigation_pass=result['navigation_pass'],
        failures=result['navigation_failures'],flight_s=grade['full_grade']['flight_time_s'],
        clearance_m=grade['measured_corridor_clearance_m'],exclusion_clearance_m=grade['measured_red_clearance_m'],
        final_disarmed=True,files=files,forecast=dict(bytes=forecast.stat().st_size,sha256=hashlib.sha256(forecast.read_bytes()).hexdigest())))
review=dict(closed_trials=10,navigation_passes=sum(row['navigation_pass'] for row in rows),
    all_navigation_pass=False,source_archive_verified=True,source_archive_sha256=report['source_archive_sha256'],
    rows=rows,empty_camera_files_expected=True,scope='Object-level navigation only; no rendered or motor qualification',
    production_adopted=False,truth_evaluation_only=True)
with (out/'closed_batch_review.json').open('x') as handle:json.dump(review,handle,indent=2)
print(json.dumps([{k:r[k] for k in ('run','navigation_pass','failures','flight_s','clearance_m')} for r in rows],indent=2))
