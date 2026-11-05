import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
for version in ('v9','v10'):
 parent=root/f'logs/reliability_reduced_{version}_targeted_20261008'
 if not (parent/'report.json').exists():continue
 report=json.loads((parent/'report.json').read_text(encoding='utf-8'))
 manifest=json.loads((root/f'.scratch/reduced_scope_{version}_candidate_20261008/source_manifest.json').read_text())
 records=[]
 for result in report['results']:
  run=parent/result['run'];assert json.loads((run/'source_manifest.json').read_text())==manifest
  rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
  disarm=recorded_disarm(rows);assert disarm
  records.append(dict(result=result,connected_disarm=disarm,configuration=json.loads((run/'configuration.json').read_text()),operator_stop=json.loads((run/'operator_stop.json').read_text()) if (run/'operator_stop.json').exists() else None,files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
 out=root/f'logs/reliability_reduced_scope_{version}_source_20261008/targeted_diagnostic_closed_review.json'
 out.write_text(json.dumps(dict(accepted_source=False,pass_navigation=report['pass_navigation'],source_files=len(manifest),source_unchanged=report['source_unchanged'],all_connected_disarmed=True,results=records),indent=2))
 print(version,'closed',[(r['result']['run'],r['result']['navigation_pass']) for r in records])
index_path=root/'.scratch/simulation-reliability/evidence_index_20261007.json';index=json.loads(index_path.read_text(encoding='utf-8'))
for version in ('v9','v10'):index['verification'][f'{version}_targeted_closed_review']=f'logs/reliability_reduced_scope_{version}_source_20261008/targeted_diagnostic_closed_review.json'
index['active_runs']=['logs/reliability_reduced_v11_targeted_20261008/my_world_random_s3']
index['current_continuation']=dict(source='V11 provisional',source_files=914,archive_sha256='08651f2d5ae06b5504ca195012f54c8f1c90fa07b226adcc595386db9b86b866',targeted_runner='logs/reliability_reduced_v11_targeted_20261008',remaining='Targeted navigation, one final offline suite, five rendered acceptances and reduced campaign')
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
status=root/'.scratch/simulation-reliability/status.md';old=status.read_text(encoding='utf-8')
status.write_text(('''# Current checkpoint — V11 provisional

No accepted source. V11 is frozen at 914 controlled files, archive SHA256
08651f2d5ae06b5504ca195012f54c8f1c90fa07b226adcc595386db9b86b866.
Retained random seed 3 is active. Braking now captures the measured settled
position for the turn and speed-acknowledgement anchors. Speed/detector waits
freeze their hold instead of chasing every noisy pose update. Real leaf
regressions reproduced both defects and 108 relevant checks pass.
V9 and V10 field 1 passed navigation; retained random 3 failed in both,
with recorded operator RTL and actual connected disarm. Both closed reviews
preserve every grade and artifact hash. Current-source required field seeds,
final full offline, five rendered acceptances and 96 eligible campaign flights
remain pending. The 24 geometry classifications are not passes; 80 weather
cases are excluded. Strong-gust/delay failures remain unresolved/excluded.

## Prior checkpoints

'''+old).rstrip()+'\n',encoding='utf-8')
report_path=root/'.scratch/simulation-reliability/evidence_report_20261007.md';report=report_path.read_text(encoding='utf-8')
report=report.replace('active provisional source is V10','active provisional source is V11').replace('4ae04641a3a81a36e4e2dd5b0da00aa712e87d03a842340d2df86e411265bd45','08651f2d5ae06b5504ca195012f54c8f1c90fa07b226adcc595386db9b86b866').replace('reliability_reduced_scope_v10_source','reliability_reduced_scope_v11_source').replace('Field seed 1 and retained random seed 3 are active','Retained random seed 3 is active').replace('reliability_reduced_v10_targeted','reliability_reduced_v11_targeted').replace('passes **66** checks','passes **108** relevant checks')
report=report.replace('The focused search/router set','V11 additionally freezes the measured stopped pose for turn and speed-ACK holds,\nand prevents detector/speed waits from chasing new noisy pose observations.\nThe focused search/router/detector/hover set')
report=report.replace('| Strong gust/delayed control |','| V10 field 1 | All 13 navigation checks; both corridors and connected disarm, 845.7 s total sim | Different source |\n| V10 retained random 3 | Failed; operator RTL after 900 s, connected disarm | Remains in scope; moving hold anchors reproduced |\n| Strong gust/delayed control |')
report_path.write_text(report,encoding='utf-8')
