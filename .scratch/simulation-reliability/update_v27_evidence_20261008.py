"""Publish the strict-climb checkpoint while old flights close safely."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v27_source_20261008';prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v26_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v27_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],removed=[n for n in old if n not in new],accepted_source=False,acceptance_thresholds_unchanged=True,lidar_filter_unchanged=True,normal_actuators_unchanged=True)
(source/'change_from_v26.json').write_text(json.dumps(changes,indent=2))
diagnosis=root/'logs/reliability_reduced_v26_targeted_20261008/my_world_random_s3/return_climb_diagnosis.json'
d=json.loads(diagnosis.read_text());assert d['connected_disarm']
headline=f'''# Current checkpoint: V27 provisional

No accepted source. V27 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match; 226 focused checks pass. The actual
built mission reproduced the return handover failure at measured altitudes
9.41, 9.50 and 9.69 m: ClimbForReturn inherited a .60 m tolerance, while
RestoreNavigationSpeed correctly requires at least 9.70 m for a 10 m transit.
V27 finishes this particular climb within .20 m, retaining the following
.30 m guard, fresh pose, nadir settlement, acknowledgement and bounded cap.
The climb continues commanding 10 m without restoring horizontal speed early.
Other climb tolerances, target height and acceptance thresholds are unchanged.

V26 field 2 passed navigation with .7318246284671641 m minimum corridor
clearance and actual disarm. Mild random 3 found the delivery QR, but failed
at the high-return handover before return search. The original failed grade,
fresh-pose diagnosis, automatic RTL and actual disarm are preserved. The
remaining isolated V26 flights continue to close; none can qualify V27.

V27 starts its priority mild seed 3 on the already closed V26 domain 41.
Its second worker waits until the entire V26 batch closes before reusing
domain 40, maintaining at most two active flights across both candidates.
Five same-source navigation passes are still required. A failed V27 case
stops queueing unflown cases; already armed flights finish safely and retain
telemetry through actual disarm. Cancelled unflown cases are not passes.

Only five V27 targeted passes unlock one final offline suite, five full native
22/22 rendered acceptances and 96 eligible campaign flights. Reduced scope
remains 120 selected, 24 negative geometry classifications and 80 weather
exclusions. No campaign flight has qualified. Strong-gust and artificially
delayed-control failures remain unresolved and excluded. Original 200-case
qualification is not claimed. V26's conservative zero-queue certificate and
side-to-vertical framing fix are retained; no .70 m clearance or thin-obstacle
filter has been weakened.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V27 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
if '| V26 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |','| V26 mild random 3 | QR found; high-return speed guard rejected climb handover; automatic RTL and actual disarm | Original FAIL preserved; built mission reproduces .60 m/.30 m tolerance mismatch; V27 strict climb unaccepted |\n| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V27 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five V27 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v26_targeted_20261008','logs/reliability_reduced_v27_targeted_20261008'];index['active_trial']=index['active_runs'][-1]
index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v27_source_20261008/planned_geometry_scope.json'
index['verification']['v26_return_climb_diagnosis']=str(diagnosis.relative_to(root))
index['verification']['v27_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v27_source_20261008/installed_startup_imports.json',red='logs/reliability_return_climb_completion_red_20261008.log',focused='logs/reliability_v27_return_climb_focused_20261008.log',checks=226,accepted=False)
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write('\n08 October V27: V26 field 2 passed navigation with .7318246284671641 m corridor clearance and actual disarm. Mild random 3 QR found but return handover failed; automatic RTL and actual disarm preserved. Actual built mission red reproduced generic .60 m climb completing below next .30 m guard. V27 specific return climb uses .20 m tolerance, retaining 10 m height and all prerequisites. 226 focused checks and 11 startup imports match 934-file freeze. Priority V27 trial uses safely closed domain 41 while second worker waits for V26 to close domain 40. Five passes still required; failed batches stop unflown queue and never interrupt armed flights. No accepted source or campaign qualification.\n')
print(json.dumps(changes,indent=2))
