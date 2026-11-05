import hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
source=root/'logs/reliability_reduced_scope_v8_source_20261008'
parent=root/'logs/reliability_reduced_v8_targeted_20261008'
report=json.loads((parent/'report.json').read_text(encoding='utf-8'));closed=[]
for result in report['results']:
 run=parent/result['run'];rows=[json.loads(s) for s in (run/'onboard.jsonl').read_text(encoding='utf-8').splitlines()]
 disarm=recorded_disarm(rows);assert disarm,result['run']
 closed.append(dict(result=result,recorded_disarm=disarm,files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()}))
review=dict(pass_navigation=False,accepted_source=False,reason='Current-command guard repeatedly brakes its own completed hold inside inflated red margins',runs=closed,all_connected_disarmed=True,operator_abort_performed=False)
(source/'targeted_failed_closed_review.json').write_text(json.dumps(review,indent=2))
index_path=root/'.scratch/simulation-reliability/evidence_index_20261007.json';index=json.loads(index_path.read_text(encoding='utf-8'))
index['verification']['v8_targeted_failed_closed_review']=str((source/'targeted_failed_closed_review.json').relative_to(root)).replace('\\','/')
index['active_runs']=['logs/reliability_reduced_v9_targeted_20261008/my_world_field_s1','logs/reliability_reduced_v9_targeted_20261008/my_world_random_s3']
index['current_continuation']=dict(source='V9 provisional',source_files=914,archive_sha256='681ec251b87cc2f9899c2d27b6bc71345801537fbca812d56ea8b16c98204225',targeted_runner='logs/reliability_reduced_v9_targeted_20261008',remaining='Remaining targeted navigation, one final full offline suite, five same-source rendered acceptances, reduced campaign and accepted-source report')
index['reduced_scope']['normal_controller_timing_model_s']=dict(native_default=.4,zero_added_queue_navigation_fixture=0.)
index_path.write_text(json.dumps(index,indent=2),encoding='utf-8')
status_path=root/'.scratch/simulation-reliability/status.md';old=status_path.read_text(encoding='utf-8')
checkpoint='''# Current reduced qualification

No accepted final source exists. Strong-gust and artificially delayed-control
failures remain unresolved, preserved and excluded. The original 200-case
qualification is not claimed.

V9 is provisional: 914 controlled files, archive SHA256
681ec251b87cc2f9899c2d27b6bc71345801537fbca812d56ea8b16c98204225.
Field seed 1 and retained mild-weather seed 3 are being tested at RTF2,
zero extra transport queue, normal .6 s actuator response and .20 s budget.
The braking hold handoff regression reproduced the V8 deadlock before the
fix. After the fix, 65 search/router checks pass, including the real leaf
commanding a certified escape, replacement unsafe commands braking and
stale motion evidence preventing release.

All five V8 trials failed in battery-triggered RTL. Their connected FCU
disarm and artifact hashes are closed in
logs/reliability_reduced_scope_v8_source_20261008/targeted_failed_closed_review.json.
No operator abort was performed on those already closed trials.

Earlier V3 field seeds 1/2/3 passed navigation and its offline suite passed
1477 with 3 skipped; those sources differ and cannot qualify V9. V7 retained
mild-weather seed 4 passed; seed 3 spent 799.6 s searching for the delivery QR
and failed. All failures remain preserved.

Campaign plan: 120 selected weather cases, of which 96 are eligible flights
and 24 are existing invalid/infeasible geometry classifications. Another 80
weather cases are excluded. Executed campaign flights: zero. No geometry
classification is a traversal pass. Required final offline, five rendered
acceptances and reduced campaign are pending.

## Prior checkpoints

'''
status_path.write_text(checkpoint+old,encoding='utf-8')
print('V8: five failures closed with actual connected disarm; V9 pending')
