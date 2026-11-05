import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
for version in ('v11',):
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
