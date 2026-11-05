"""Close every combined candidate trial, preserving failures and truth separation."""
from collections import Counter
import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[2]
out = root/'logs/reliability_command_deadline_navigation_20261007'
source = root/'logs/reliability_command_deadline_source_20261007'
snapshot = root/'.scratch/command_deadline_candidate_20261007'
batch = json.loads((out/'report.json').read_text())
assert batch['finished_wall'] and batch['source_unchanged'] and len(batch['results']) == 3
archive = source/'frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == batch['source_archive_sha256']
with zipfile.ZipFile(archive) as handle:
    frozen = json.loads(handle.read('source_manifest.json'))
    for name, sha in frozen.items():
        assert hashlib.sha256(handle.read(name)).hexdigest() == sha
        assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest() == sha
for name, sha in batch['asset_sha256'].items():
    assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest() == sha
reviews = []
required = ('configuration.json','world_spec.json','layout.json','source_manifest.json',
    'onboard.jsonl','onboard_lidar.jsonl','flight_commands.jsonl','winch_commands.jsonl',
    'detector_events.jsonl','evaluation_truth_track.csv','independent_command_receipt_timing.json',
    'navigation_grade.json','run.json','stack.log')
for result in batch['results']:
    assert result['harness_valid'] and result['source_matches_frozen']
    run = out/result['run']
    assert json.loads((run/'source_manifest.json').read_text()) == frozen
    grade = json.loads((run/'navigation_grade.json').read_text())
    assert grade['full_grade']['final_armed'] is False
    assert (run/'track.csv').read_bytes() == (run/'evaluation_truth_track.csv').read_bytes()
    forecast = out/(result['run']+'_forecasts.json')
    records = json.loads(forecast.read_text())['records']
    review = dict(run=result['run'], navigation_pass=grade['pass_navigation'],
        clearance_m=grade['measured_corridor_clearance_m'], exclusion_clearance_m=grade['measured_red_clearance_m'],
        sampling_reserve_pass=grade['measured_corridor_clearance_m'] >= .725 and
            grade['checks']['outbound lane flown THROUGH the corridor'] and grade['checks']['return lane flown THROUGH the corridor'],
        flight_s=grade['full_grade']['flight_time_s'], final_disarmed=True,
        navigation_failures=result['navigation_failures'], source_files=len(frozen), source_verified=True, assets_verified=True,
        files={name:dict(bytes=(run/name).stat().st_size, sha256=hashlib.sha256((run/name).read_bytes()).hexdigest()) for name in required},
        forecast_sha256=hashlib.sha256(forecast.read_bytes()).hexdigest(), control_fault_counts=dict(Counter(r['detail'].get('fault','none') for r in records)),
        production_adopted=False, rendered_perception_qualified=False, motor_delivery_qualified=False, truth_evaluation_only=True)
    reviews.append(review)
    print(json.dumps({k:v for k,v in review.items() if k!='files'}), flush=True)
with (out/'closed_batch_review.json').open('x') as stream:
    json.dump(dict(source_archive_verified=True, source_unchanged=True, all_trials_disarmed=True, trials=reviews), stream, indent=2)
