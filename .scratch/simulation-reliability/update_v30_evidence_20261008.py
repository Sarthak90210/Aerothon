"""Register the unaccepted capture-gap candidate and its exact-source gates."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v30_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v30_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v29_candidate_20261008/source_manifest.json').read_text())
provenance=json.loads((source/'provenance.json').read_text())
(source/'change_from_v29.json').write_text(json.dumps(dict(accepted_source=False,changed=[n for n in new if n in old and new[n]!=old[n]],added=[n for n in new if n not in old],thresholds_unchanged=True,normal_response_s=.6,extra_queue_s=0.),indent=2))
head=f'''# Current checkpoint: V30 provisional, targeted verification active

V30 freezes {len(new)} controlled files. Archive SHA256
{provenance['archive_sha256']}. The change retains the latest visual horizontal
landing correction during the existing brief-loss grace period while holding
current height. Prolonged loss still invokes the original recovery; no descent
continues without visual lock. The actual descent regression went RED before
the fix; 52 focused checks passed after it. The simplified 10.79-second landing
physics replay does not reproduce the full failure and is not whole-flight
evidence. All previous failures and all acceptance thresholds remain intact.

Five targeted cases now run on this source with normal actuator behaviour and
zero injected delay. Only five passes unlock one final offline suite, five
full rendered acceptances, and the 96 eligible campaign flights. No accepted
source exists. Strong gusts and artificially delayed control remain unresolved,
preserved and excluded. No original 200-case qualification is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V30 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V29 timing failures |' not in s:
 s=s.replace('| Strong gust/delayed control |','| V29 timing failures | Mild random 3 and field 3 exceeded 900 s; both zero contacts/fence breaches, all corridor checks passed, automatic RTL and actual connected disarm recorded; field 2 navigation PASS with DEGRADED precision | Original failures retained in exact-source closed review; two unflown cancelled; V30 capture-gap correction unaccepted |\n| Strong gust/delayed control |',1)
 f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V30 provisional',source_files=len(new),archive_sha256=provenance['archive_sha256'],remaining='Five V30 targeted trials, final offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v30_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v30_focused']=dict(red='logs/reliability_landing_capture_gap_red_20261008.log',focused='logs/reliability_v30_landing_focused_20261008.log',checks=52,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V30 registered as provisional; qualification gates remain pending')
