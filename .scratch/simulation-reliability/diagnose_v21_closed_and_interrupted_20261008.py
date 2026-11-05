"""Retain partial batch grades; an armed interrupted run is never a pass."""
import bisect,hashlib,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[2];parent=root/'logs/reliability_reduced_v21_targeted_20261008'
records=[]
for run in sorted(parent.glob('my_world_*')):
    rows=[]
    for line in (run/'onboard.jsonl').open():
        try:rows.append(json.loads(line))
        except ValueError:pass
    changes=[];previous=None
    for row in rows:
        if row.get('mission') and row['mission']!=previous:
            changes.append([row['stamp'],row['mission']]);previous=row['mission']
    flight=next(r for r in reversed(rows) if 'flight' in r)
    grade_path=run/'navigation_grade.json'
    records.append(dict(run=run.name,closed=grade_path.exists(),last_stamp=flight['stamp'],
        last_flight=flight['flight']['data'],actual_disarm=flight['flight']['data']['armed'] is False,
        original_grade=json.loads(grade_path.read_text()) if grade_path.exists() else None,
        phase_changes=changes,configuration=json.loads((run/'configuration.json').read_text()),
        files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
review=dict(accepted_source=False,qualification_complete=False,batch_complete=False,
    reason='Owning process handle missing and live WSL process inventory has no simulator processes; WSL uptime reset. Last run still armed in retained telemetry, disarm unverified.',
    results=records)
source=root/'logs/reliability_reduced_scope_v21_source_20261008'
with (source/'interrupted_batch_closed_review.json').open('x') as f:json.dump(review,f,indent=2)
for r in records:
    g=r['original_grade'];print(json.dumps(dict(run=r['run'],actual_disarm=r['actual_disarm'],
        failures=[k for k,v in g['checks'].items() if not v] if g else ['interrupted; final grade and disarm missing'],
        phases=[p for p in r['phase_changes'] if p[0]>500])))
run=parent/'my_world_field_s2';lidar=[]
for line in (run/'onboard_lidar.jsonl').open():
    r=json.loads(line);stamp=r['data']['header']['stamp'];t=stamp['sec']+stamp['nanosec']*1e-9
    if 690.5<r['received_stamp']<692.:lidar.append(dict(received=r['received_stamp'],capture=t,age=r['received_stamp']-t))
(run/'gate_timestamp_failure_diagnosis.json').write_text(json.dumps(dict(qualification=False,recorded_lidar=lidar,
    limitation='Recorder and controller are separate subscriptions; a recorder receipt does not prove controller arrival order.'),indent=2))
print('LIDAR',json.dumps(lidar))
