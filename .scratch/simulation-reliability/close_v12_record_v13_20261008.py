import hashlib,json,sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
version='v12';parent=root/f'logs/reliability_reduced_{version}_targeted_20261008'
report=json.loads((parent/'report.json').read_text(encoding='utf-8'));records=[]
manifest=json.loads((root/f'.scratch/reduced_scope_{version}_candidate_20261008/source_manifest.json').read_text())
for result in report['results']:
 run=parent/result['run'];assert json.loads((run/'source_manifest.json').read_text())==manifest
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
 disarm=recorded_disarm(rows);assert disarm
 records.append(dict(result=result,connected_disarm=disarm,configuration=json.loads((run/'configuration.json').read_text()),operator_stop=json.loads((run/'operator_stop.json').read_text()),files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
(root/f'logs/reliability_reduced_scope_{version}_source_20261008/targeted_diagnostic_closed_review.json').write_text(json.dumps(dict(accepted_source=False,pass_navigation=False,source_unchanged=report['source_unchanged'],source_files=len(manifest),all_connected_disarmed=True,results=records),indent=2))
index_path=root/'.scratch/simulation-reliability/evidence_index_20261007.json';index=json.loads(index_path.read_text(encoding='utf-8'))
for version in ('v11','v12'):index['verification'][f'{version}_targeted_closed_review']=f'logs/reliability_reduced_scope_{version}_source_20261008/targeted_diagnostic_closed_review.json'
index['active_runs']=['logs/reliability_reduced_v13_targeted_20261008/my_world_random_s3']
index['current_continuation']=dict(source='V13 provisional',source_files=916,archive_sha256='5159a424f99dbaf793204ef3061e6dacf7b949565bd4137313ffde20c6fdbcd8',targeted_runner='logs/reliability_reduced_v13_targeted_20261008',remaining='Targeted navigation, one final offline suite, five rendered acceptances and reduced campaign')
index['reduced_scope'].update(camera_capture_hz=20,lidar_scan_hz=10,classification_audit='logs/reliability_reduced_scope_v12_source_20261008/planned_geometry_scope.json')
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
status=root/'.scratch/simulation-reliability/status.md';old=status.read_text(encoding='utf-8')
status.write_text(('''# Current checkpoint — V13 provisional

No accepted source. Frozen source: 916 controlled files, archive SHA256
5159a424f99dbaf793204ef3061e6dacf7b949565bd4137313ffde20c6fdbcd8.
Retained random seed 3 is active. Search braking consumes actual delivered
FCU velocity captures instead of snapshots of that stream at the slower
mission timer. The unchanged .10 m/s threshold, three distinct fresh captures,
post-brake epoch and intervening-motion resets are covered at the real callback
and leaf seams. Earlier code both missed valid settled intervals and missed
motion between leaf snapshots; both red controls are archived. 137 focused
checks pass. Return-gate .08 m/s and .3 s stability requirements are unchanged.

The object fixture camera now matches the native model's existing 20 Hz;
lidar remains 10 Hz, physics and actuator response unchanged, configured frame
drops and latency retained. This mismatch has a red real-run-loop regression
and native sensor-definition comparison. Rates are explicit per-run metadata.
V11 and V12 retained random 3 failed time and ended in recorded RTL and actual
connected disarm. Their failure grades, configurations and hashes are closed.
Final field seeds, offline suite, five rendered runs and 96 eligible campaign
flights remain pending. The 24 negative geometry classifications are not
passes, and 80 weather cases are excluded. Strong-gust/delay failures remain
unresolved, preserved and excluded from current qualification.

## Prior checkpoints

'''+old).rstrip()+'\n',encoding='utf-8')
report_path=root/'.scratch/simulation-reliability/evidence_report_20261007.md';text=report_path.read_text(encoding='utf-8')
text=text.replace('active provisional source is V11: 914','active provisional source is V13: 916').replace('08651f2d5ae06b5504ca195012f54c8f1c90fa07b226adcc595386db9b86b866','5159a424f99dbaf793204ef3061e6dacf7b949565bd4137313ffde20c6fdbcd8').replace('reliability_reduced_scope_v11_source','reliability_reduced_scope_v13_source').replace('reliability_reduced_v11_targeted','reliability_reduced_v13_targeted').replace('passes **108** relevant checks','passes **137** relevant checks').replace('reliability_reduced_scope_v8_source_20261008/planned_geometry_scope.json','reliability_reduced_scope_v12_source_20261008/planned_geometry_scope.json')
text=text.replace('Required thresholds remain', '''V13 consumes actual delivered FCU velocity samples for search braking. All
three captures must remain distinct, fresh, after the brake command, and at or
below the existing .10 m/s limit; intervening motion resets the streak. Real
callback/leaf controls reproduce missed short settled intervals and previously
missed movement between leaf snapshots. Return-gate stability limits are intact.

A fixture scheduling defect tied camera captures to the 10 Hz lidar timer,
while both native vehicle definitions specify 20 Hz. The corrected object
fixture matches the existing native rate. Drops and latency are retained, and
per-run configuration now explicitly records 20 Hz camera and 10 Hz lidar.
The production native camera rate was not increased. Earlier 10 Hz fixture
results cannot qualify this source/configuration.

Required thresholds remain''')
text=text.replace('| Strong gust/delayed control |','| V11 retained random 3 | QR found at 802 s; failed time and return; recorded RTL/disarm | Remains in scope |\n| V12 retained random 3 | Failed QR time; recorded RTL/disarm; normal native-matching camera cadence | Remains in scope; FCU sample aliasing reproduced |\n| Strong gust/delayed control |')
report_path.write_text(text,encoding='utf-8')
print('V12 failure closed; report tracks V13 pending qualification')
