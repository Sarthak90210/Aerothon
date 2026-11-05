"""Preserve every closed parallel result without upgrading its failed grade."""
import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
parent=root/'logs/reliability_reduced_v17_targeted_20261008'
report=json.loads((parent/'report.json').read_text());assert report['pass_navigation'] is False
manifest=json.loads((root/'.scratch/reduced_scope_v17_candidate_20261008/source_manifest.json').read_text());records=[]
for result in report['results']:
    run=parent/result['run'];assert json.loads((run/'source_manifest.json').read_text())==manifest
    rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
    disarm=recorded_disarm(rows);assert disarm
    records.append(dict(result=result,grade=json.loads((run/'navigation_grade.json').read_text()),configuration=json.loads((run/'configuration.json').read_text()),connected_disarm=disarm,
                        files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
out=root/'logs/reliability_reduced_scope_v17_source_20261008/parallel_targeted_closed_review.json'
review=dict(source_files=len(manifest),source_unchanged=report['source_unchanged'],accepted_source=False,pass_navigation=False,results=records,
            concurrent_flights=5,full_offline_suite_concurrent=True,watcher_failure='OSError [Errno 61] No data available while reading active Windows/WSL evidence file; no abort receipt was issued; every case later disarmed')
with out.open('x') as f:json.dump(review,f,indent=2)
base=root/'.scratch/simulation-reliability';p=base/'evidence_index_20261007.json';idx=json.loads(p.read_text(encoding='utf-8'))
idx['verification'].update(v17_parallel_targeted_closed_review=str(out.relative_to(root)),v17_final_full_offline='logs/reliability_reduced_scope_v17_source_20261008/full_offline_closed_review.json',v17_field_1_clearance_diagnosis='logs/reliability_reduced_v17_targeted_20261008/my_world_field_s1/return_clearance_diagnosis.json')
idx['active_runs']=['logs/reliability_reduced_v17_normal_timing_retry_20261008']
idx['current_continuation']['remaining']='Three same-source/configuration focused timing probes active; all five rendered acceptances and 96 reduced campaign flights pending'
p.write_text(json.dumps(idx,indent=2),encoding='utf-8')
print('All five parallel results and actual disarms closed; failed grades preserved')
