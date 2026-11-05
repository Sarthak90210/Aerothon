"""Track the two reproduced defects; preserve the failed V25 qualification."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v26_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v25_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v26_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],removed=[n for n in old if n not in new],accepted_source=False,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_actuators_unchanged=True)
(source/'change_from_v25.json').write_text(json.dumps(changes,indent=2))
closed_path=root/'logs/reliability_reduced_scope_v25_source_20261008/targeted_failure_closed_review.json'
closed=json.loads(closed_path.read_text());assert len(closed['results'])==5
summary=[]
for r in closed['results']:
    g=r['grade'];summary.append(dict(run=r['result']['run'],pass_navigation=g['pass_navigation'],failures=[k for k,v in g['checks'].items() if not v],airborne_s=g['full_grade']['flight_time_s'],corridor_m=g['measured_corridor_clearance_m'],connected_disarm=r['connected_disarm']))
headline=f'''# Current checkpoint: V26 provisional

No accepted source. V26 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match. 122 integrated focused checks and 24
normal navigation/timing checks pass. Two actual decision seams reproduced
defects before their respective fixes:

* FindReturnBanner used one retry key for both a side crop and the horizontally
  centred vertical crop at the same vantage/tilt. Centring consumed the later
  vertical recovery. V26 includes horizontal completeness in the key. Each
  framing class still receives only one retry after distinct fresh captures;
  camera settlement and the three-adjustment tilt bound remain required.
  Clipped range remains unusable and cannot authorize gate crossing.
* The actual motion certificate skipped its zero-disturbance prediction when
  transport queue was zero. A modest .06 m/s helpful response error authorized
  a packet whose actual .6 s response/braking tail reduced clearance to
  0.6990529898953362 m. The frozen V25 publication method reproduces this with
  the normal .20 s computation budget. V26 requires both predictions even with
  zero queue. A prior narrow (.85 m) forecast test now checks refusal rather
  than authorizing a packet safe only if the estimated disturbance occurs.
  A separate wider case proves forecast compensation remains available when
  both predictions preserve the same .70 m minimum. No threshold was reduced.

V25 closed four navigation passes. Fields 1/2/3 and mild random 4 completed
and actually disarmed. Mild random 3 found its delivery QR but spent 190.85 s
in return-gate search; it failed time/unexpected mode and actual corridor
clearance 0.6849396857248734 m. Watchdog RTL was requested only after the
unchanged 900 s airborne limit; recording continued through actual disarm.
All five closed with zero contacts/fence breaches. Mild random 4 reported
DEGRADED precision, retained as a quality limitation. The exact-source closed
review preserves every failed grade and artifact. Fixture delivery remains
unmeasured and unqualified. No full offline suite was run on failed V25.

Five V26 two-worker targeted trials are active with normal .6 s response,
20 Hz camera/10 Hz lidar, .20 s computation budget and zero artificial queue.
Only five same-source navigation passes unlock one final offline suite, then
five native 22/22 rendered acceptances and 96 eligible campaign flights.
Reduced scope is 120 selected, 24 negative geometry classifications and 80
weather exclusions. No campaign flight has qualified. Strong-gust and
artificially delayed-control failures remain unresolved and excluded.
Original 200-case qualification is not claimed.

Isolated V24 corridor probes are diagnostic only. Full-entry regenerated-noise,
normal-computation and full-attitude variants passed; 12 other normal lidar
realizations also passed. Starting from the recorded near-boundary state
reproduced a .69172 m deficit, but does not prove what caused the approach.
The coherent .04 m outward-bias probe also passed and its original filename
containing "red" does not make it a reproduced failure. All diagnostic verdicts
are preserved; none replaces full-flight or native acceptance. The new modest
response-error seam proves a certificate gap, not exact causation of every
older runtime failure. Final source qualification remains required.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V26 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
if '| V25 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |','| V25 mild random 3 | QR found; return search 190.85 s; actual corridor clearance 0.6849396857248734 m; time/unexpected mode failed; actual disarm | Original FAIL preserved; V26 fixes proven framing and certificate gaps, runtime acceptance pending |\n| V25 mild random 4 | Navigation passed; landing DEGRADED | Quality limitation; fixture motor delivery unqualified |\n| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V26 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five V26 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v26_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v26_source_20261008/planned_geometry_scope.json'
index['verification']['v25_closed_targeted']=dict(path=str(closed_path.relative_to(root)),results=summary,accepted=False)
index['verification']['v26_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v26_source_20261008/installed_startup_imports.json',framing_red='logs/reliability_side_vertical_crop_red_20261008.log',certificate_red='logs/reliability_zero_queue_normal_budget_red_20261008.log',focused='logs/reliability_v26_integrated_focused_20261008.log',focused_checks=122,normal_navigation='logs/reliability_v26_normal_navigation_focused_20261008.log',normal_checks=24,accepted=False)
index['verification']['v25_crop_diagnosis']='logs/reliability_reduced_v25_targeted_20261008/my_world_random_s3/return_crop_sequence_diagnosis.json'
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write('\n08 October V26: V25 closed four navigation passes; all actually disarmed and zero contacts/fence breaches. Mild random 3 QR found, return search 190.85 s, corridor 0.6849396857248734 m/time/mode FAIL preserved. Actual leaf reproduced side-crop retry consuming centred vertical framing. Actual frozen V25 certificate reproduced .6990529898953362 m clearance with modest .06 m/s helpful response error, normal .20 s budget/.6 s response/zero queue. V26 separates framing classes and enforces both disturbance and zero-disturbance predictions. 122 integrated and 24 normal navigation/timing checks pass; 11 normal-startup imports match 933-file freeze. Five two-worker targeted trials active; no accepted source or reduced qualification yet. Strong/delayed failures unresolved and excluded.\n')
print(json.dumps(changes,indent=2))
