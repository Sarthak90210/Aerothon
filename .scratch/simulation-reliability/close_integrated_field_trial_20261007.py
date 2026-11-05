"""Close code/assets, captures and FCU disarm for an object-level field trial."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
label=sys.argv[1];seed=int(sys.argv[2]) if len(sys.argv)>2 else 2
if label in ('fine','scoped','clip','arrival'):
 prefix={'fine':'fine_return_framing','scoped':'scoped_fine_framing','clip':'clipped_bearing_framing','arrival':'arrival_anchor_framing'}[label]
 source=root/f'logs/reliability_{prefix}_source_20261007'
 snapshot=root/f'.scratch/{prefix}_candidate_20261007'
 out=root/f'logs/reliability_{prefix}_field_s{seed}_navigation_20261007'
elif label=='monotonic':
 source=root/'logs/reliability_monotonic_search_escape_source_20261007'
 snapshot=root/'.scratch/monotonic_search_escape_candidate_20261007'
 out=root/f'logs/reliability_monotonic_search_escape_field_s{seed}_navigation_20261007'
elif label=='certified':
 source=root/'logs/reliability_certified_search_escape_source_20261007'
 snapshot=root/'.scratch/certified_search_escape_candidate_20261007'
 out=root/f'logs/reliability_certified_search_escape_field_s{seed}_navigation_20261007'
elif label=='oblique':
 source=root/'logs/reliability_oblique_observer_source_20261007'
 snapshot=root/'.scratch/oblique_observer_candidate_20261007'
 out=root/f'logs/reliability_oblique_observer_field_s{seed}_navigation_20261007'
else:
 assert label=='integrated'
 source=root/'logs/reliability_integrated_field2_source_20261007'
 snapshot=root/'.scratch/integrated_field2_candidate_20261007'
 out=root/'logs/reliability_integrated_field2_navigation_assets_retry_20261007'
report=json.loads((out/'report.json').read_text());assert report['finished_wall'] and report['source_unchanged'] and report['run_manifest_matches_frozen'] and report['asset_unchanged']
archive=source/'frozen_source.zip';assert hashlib.sha256(archive.read_bytes()).hexdigest()==report['archive_sha256']
with zipfile.ZipFile(archive) as z:
 frozen=json.loads(z.read('source_manifest.json'))
 for name,sha in frozen.items():
  assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
  assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
for name,sha in report['asset_sha256'].items():assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
run=out/f'my_world_field_s{seed}';grade=json.loads((run/'navigation_grade.json').read_text())
assert grade['full_grade']['final_armed'] is False
rows=[json.loads(line) for line in (run/'onboard.jsonl').open()]
flight=[r for r in rows if (r.get('flight') or {}).get('data',{}).get('armed') is True];assert flight
last_flight=rows[-1]['flight']['data'];assert last_flight['connected'] and not last_flight['armed']
arm_end=max(r['stamp'] for r in flight)
events=[json.loads(line) for line in (run/'camera_capture_events.jsonl').open()]
camera_through_disarm=bool(events) and max(e['capture_stamp'] for e in events)>=arm_end
# This object-level fixture emits detections, not rendered camera images.
# Preserve the empty camera channel explicitly; it cannot qualify recording.
assert (run/'track.csv').read_bytes()==(run/'evaluation_truth_track.csv').read_bytes()
required=('source_manifest.json','configuration.json','layout.json','world_spec.json','onboard.jsonl','onboard_lidar.jsonl','camera_capture_events.jsonl','flight_commands.jsonl','detector_events.jsonl','evaluation_truth_track.csv','navigation_grade.json','recorded_result.json')
review=dict(scope='Object-level navigation and telemetry only; no rendered or motor delivery qualification',source_archive_verified=True,source_unchanged=True,assets_verified=True,connected_disarm_recorded=True,independent_command_receipt_recording_present=(run/'independent_command_receipt_timing.json').exists(),camera_captures_through_last_armed_sample=camera_through_disarm,rendered_camera_qualified=False,navigation_pass=grade['pass_navigation'],flight_time_s=grade['full_grade']['flight_time_s'],corridor_clearance_m=grade['measured_corridor_clearance_m'],red_clearance_m=grade['measured_red_clearance_m'],navigation_failures=report['result']['navigation_failures'],production_adopted=False,files={name:dict(bytes=(run/name).stat().st_size,sha256=hashlib.sha256((run/name).read_bytes()).hexdigest()) for name in required})
fixture=json.loads((run/'run.json').read_text())
review['independent_fixture_contacts']=fixture.get('contacts')
review['independent_fixture_contact_free']=fixture.get('contacts')==[]
review['legacy_or_current_grade_contact_verdict']=grade['checks']['no obstacle contact'] if 'checks' in grade else grade['full_grade']['checks']['no obstacle contact']
review['files']['run.json']=dict(bytes=(run/'run.json').stat().st_size,sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest())
with (out/'closed_trial_review_20261007.json').open('x') as f:json.dump(review,f,indent=2)
print(json.dumps({k:v for k,v in review.items() if k!='files'},indent=2))
