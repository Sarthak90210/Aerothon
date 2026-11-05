"""Close all three navigation seeds, preserving the DDS startup failure."""
import hashlib,json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
snapshot=root/'.scratch/reduced_scope_v3_candidate_20261008'
source=root/'logs/reliability_reduced_scope_v3_source_20261008'
manifest=json.loads((snapshot/'source_manifest.json').read_text())
archive=source/'frozen_source.zip';provenance=json.loads((source/'provenance.json').read_text())
assert hashlib.sha256(archive.read_bytes()).hexdigest()==provenance['archive_sha256']
with zipfile.ZipFile(archive) as z:
 for name,sha in manifest.items():
  assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
  assert hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha,name
results=[]
for seed in (1,2,3):
 parent='reliability_reduced_v3_seed2_dds_retry_20261008' if seed==2 else 'reliability_reduced_v3_seed_trials_20261008'
 run=root/f'logs/{parent}/my_world_field_s{seed}'
 grade=json.loads((run/'navigation_grade.json').read_text());assert grade['pass_navigation'] and all(grade['checks'].values())
 configuration=json.loads((run/'configuration.json').read_text())
 assert configuration['injected_command_delay_s']==0 and configuration['vel_response_s']==.6
 assert json.loads((run/'source_manifest.json').read_text())==manifest
 fixture=json.loads((run/'run.json').read_text());assert fixture['contacts']==[] and fixture['fence_breaches']==0
 rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text().splitlines()]
 disarm=recorded_disarm(rows);assert disarm,seed
 result=dict(seed=seed,path=str(run.relative_to(root)),checks=len(grade['checks']),pass_navigation=True,
   flight_time_s=grade['full_grade']['flight_time_s'],corridor_clearance_m=grade['measured_corridor_clearance_m'],
   red_clearance_m=grade['measured_red_clearance_m'],connected_disarm=disarm,configuration=configuration,
   files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()},
   rendered_qualified=False,delivery_qualified=False)
 results.append(result)
review=dict(scope='Three object-level moderate-field navigation seeds, zero injected queue; rendered and motor delivery separately required',
 source_unchanged=True,source_archive_verified=True,source_files=len(manifest),seeds=results,pass_navigation=True,
 startup_failure_preserved='logs/reliability_reduced_v3_seed_trials_20261008/my_world_field_s2',accepted_source=False)
with (source/'three_seed_closed_review.json').open('x') as f:json.dump(review,f,indent=2)
print(json.dumps([{k:v for k,v in r.items() if k not in ('files','configuration','connected_disarm')} for r in results],indent=2))
