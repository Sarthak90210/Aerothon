"""Close all five targeted navigation cases on the exact V14 freeze."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
snapshot=root/'.scratch/reduced_scope_v22_candidate_20261008';source=root/'logs/reliability_reduced_scope_v22_source_20261008'
manifest=json.loads((snapshot/'source_manifest.json').read_text());archive=source/'frozen_source.zip';provenance=json.loads((source/'provenance.json').read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['archive_sha256']
with zipfile.ZipFile(archive) as z:
 for name,sha in manifest.items():
  assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
  assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
results=[]
for weather,seed in [('random',3),('field',1),('field',2),('field',3),('random',4)]:
 parent=root/'logs/reliability_reduced_v22_targeted_20261008'
 assert json.loads((parent/'report.json').read_text())['pass_navigation']
 run=parent/f'my_world_{weather}_s{seed}'
 grade=json.loads((run/'navigation_grade.json').read_text());assert grade['pass_navigation'] and len(grade['checks'])==13 and all(grade['checks'].values())
 cfg=json.loads((run/'configuration.json').read_text());assert cfg['injected_command_delay_s']==0 and cfg['vel_response_s']==.6 and cfg['rtf']==2 and cfg['camera_capture_hz']==20 and cfg['lidar_scan_hz']==10
 assert not cfg['artificial_transport_delay_injected'] and cfg['navigation_only']
 assert json.loads((run/'source_manifest.json').read_text())==manifest
 fixture=json.loads((run/'run.json').read_text());assert fixture['contacts']==[] and fixture['fence_breaches']==0
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()];disarm=recorded_disarm(rows);assert disarm
 results.append(dict(weather=weather,seed=seed,path=str(run.relative_to(root)),checks=grade['checks'],flight_time_s=grade['full_grade']['flight_time_s'],corridor_clearance_m=grade['measured_corridor_clearance_m'],red_clearance_m=grade['measured_red_clearance_m'],connected_disarm=disarm,configuration=cfg,files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()},rendered_qualified=False,delivery_qualified=False))
review=dict(scope='Three moderate field and two retained mild-weather navigation seeds; normal timing/actuators, zero added delay, native-matching sensor rates',source_unchanged=True,source_archive_verified=True,source_files=len(manifest),results=results,pass_navigation=True,accepted_source=False)
with (source/'targeted_closed_review.json').open('x') as f:json.dump(review,f,indent=2)
print('Five targeted navigation cases closed; native acceptance remains required')
