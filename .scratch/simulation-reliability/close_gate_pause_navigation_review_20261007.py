"""Verify immutable candidate and closed navigation evidence without widening scope."""
from collections import Counter
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=(root/sys.argv[1]).resolve();assert out.is_relative_to((root/'logs').resolve())
report=json.loads((out/'report.json').read_text());assert report['state']=='COMPLETED'
result=report['result'];run=out/result['run']
archive=root/'logs/reliability_gate_pause_navigation_source_20261007/frozen_source.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==report['source_archive_sha256']
snapshot=root/'.scratch/gate_pause_motion_candidate_20261007'
with zipfile.ZipFile(archive) as source:
    frozen=json.loads(source.read('source_manifest.json'))
    for name,sha in frozen.items():
        assert hashlib.sha256(source.read(name)).hexdigest()==sha
        assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha
for name,sha in report['asset_sha256'].items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha
assert json.loads((run/'source_manifest.json').read_text())==frozen
grade=json.loads((run/'navigation_grade.json').read_text());assert not grade['full_grade']['final_armed']
assert (run/'track.csv').read_bytes()==(run/'evaluation_truth_track.csv').read_bytes()
forecast=out/'motion_forecasts.json';records=json.loads(forecast.read_text())['records']
faults=Counter(row['detail'].get('fault','none') for row in records)
required=('configuration.json','world_spec.json','layout.json','source_manifest.json',
    'onboard.jsonl','onboard_lidar.jsonl','flight_commands.jsonl','winch_commands.jsonl',
    'detector_events.jsonl','evaluation_truth_track.csv','independent_command_receipt_timing.json',
    'navigation_grade.json','run.json','stack.log')
review=dict(navigation_pass=grade['pass_navigation'],clearance_m=grade['measured_corridor_clearance_m'],
    sampled_clearance_meets_reserve=grade['measured_corridor_clearance_m']>=.725,
    sampling_reserve_pass=grade['measured_corridor_clearance_m']>=.725 and
        grade['checks']['outbound lane flown THROUGH the corridor'] and
        grade['checks']['return lane flown THROUGH the corridor'],
    exclusion_clearance_m=grade['measured_red_clearance_m'],flight_s=grade['full_grade']['flight_time_s'],
    final_disarmed=True,source_files=len(frozen),source_archive_verified=True,assets_verified=True,
    source_unchanged=True,files={name:dict(bytes=(run/name).stat().st_size,
        sha256=hashlib.sha256((run/name).read_bytes()).hexdigest()) for name in required},
    forecast_sha256=hashlib.sha256(forecast.read_bytes()).hexdigest(),control_records=len(records),
    control_fault_counts=dict(faults),production_adopted=False,rendered_perception_qualified=False,
    motor_delivery_qualified=False,truth_evaluation_only=True)
with (out/'closed_trial_review.json').open('x') as handle:json.dump(review,handle,indent=2)
print(json.dumps({k:v for k,v in review.items() if k!='files'},indent=2))
