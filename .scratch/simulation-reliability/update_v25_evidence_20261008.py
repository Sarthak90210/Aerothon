"""Publish the exact checkpoint; diagnostic passes are not qualification."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v25_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v24_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v25_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],removed=[n for n in old if n not in new],accepted_source=False,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_actuators_unchanged=True)
(source/'change_from_v24.json').write_text(json.dumps(changes,indent=2))
closed_path=root/'logs/reliability_reduced_scope_v24_source_20261008/targeted_failure_closed_review.json'
closed=json.loads(closed_path.read_text());assert len(closed['results'])==5
summary=[]
for r in closed['results']:
    g=r['grade'];summary.append(dict(run=r['result']['run'],pass_navigation=g['pass_navigation'],failures=[k for k,v in g['checks'].items() if not v],airborne_s=g['full_grade']['flight_time_s'],corridor_m=g['measured_corridor_clearance_m'],connected_disarm=r['connected_disarm']))
headline=f'''# Current checkpoint: V25 provisional

No accepted source. V25 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match; 297 focused checks pass. The actual
AlignToBanner transit reproduced a premature cancellation of the requested
2 m camera framing backoff: a still-clipped identified view passed the legacy
near-view shortcut before the backoff completed. V25 requires a complete view
for that shortcut. It preserves the existing complete near-board stop and
the bounded backoff, gate braking, perception and camera capture scheduling.

V24 closed with four of five navigation passes. Field seeds 1/2/3 and mild
random 4 passed navigation and actually disarmed with zero contacts/fence
breaches. Mild random 3 also completed and actually disarmed, but its actual
minimum corridor clearance was 0.6948520402727778 m, below the unchanged
0.70 m requirement. Airborne time was 792.1 s. This original failed grade,
source/configuration and all artifacts are preserved in the closed review.
Mild random 4's DEGRADED landing is retained as a quality limitation. Fixture
delivery is unmeasured and does not qualify motor delivery.

V25 same-source targeted trials are active with two workers, normal .6 s
actuator response, native-matching 20 Hz camera/10 Hz lidar, .20 s computation
budget and no injected transport queue. Five navigation passes are required
before one final offline suite, five full native 22/22 rendered acceptances
and 96 eligible campaign flights. No campaign flight has yet qualified.
Reduced scope remains 120 selected, 24 negative geometry classifications and
80 weather exclusions. Strong-gust and artificial delayed-control failures
remain unresolved and excluded. Original 200-case qualification is not claimed.

The V24 clearance minimum occurred in RETURN_CORRIDOR near obstacle 1.
At that sample the controller was BLOCKED, published zero horizontal velocity,
and reported no certified braking clearance. Measured lidar clearance was
0.70830 m while independent truth was 0.69485 m. Two isolated actual-controller
and normal-aircraft probes passed, at 0.72785 and 0.73045 m respectively. They
regenerated lidar streams and omit live ROS ordering, so neither reproduces
the runtime failure or qualifies a source. No speculative clearance change
has been made.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V25 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
if '| V24 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |','| V24 mild random 3 | Actual clearance 0.6948520402727778 m; 792.1 s airborne; mission completed and actually disarmed | Original clearance FAIL preserved; isolated probes do not reproduce runtime |\n| V24 mild random 4 | Navigation passed; landing DEGRADED | Quality limitation; fixture motor delivery unqualified |\n| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V25 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five V25 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v25_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v25_source_20261008/planned_geometry_scope.json'
index['verification']['v24_closed_targeted']=dict(path=str(closed_path.relative_to(root)),results=summary,accepted=False)
index['verification']['v25_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v25_source_20261008/installed_startup_imports.json',red='logs/reliability_clipped_backoff_transit_red_20261008.log',focused='logs/reliability_v25_clipped_backoff_focused_20261008.log',checks=297,accepted=False)
index['verification']['v24_clearance_diagnosis']='logs/reliability_reduced_v24_targeted_20261008/my_world_random_s3/corridor_clearance_diagnosis.json'
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write('\n08 October V25: V24 closed four navigation passes; all actually disarmed and zero contacts/fence breaches. Mild random 3 actual clearance 0.6948520402727778 m remains FAIL. V25 fixes actual premature clipped-backoff transit cancellation, with 297 focused passes and 11 normal-startup imports matching 931-file freeze. Two isolated corridor probes passed but did not reproduce runtime; no speculative clearance change. Five V25 targeted trials active. No accepted source, native final acceptance or campaign qualification. Strong/delayed failures unresolved and excluded.\n')
print(json.dumps(changes,indent=2))
