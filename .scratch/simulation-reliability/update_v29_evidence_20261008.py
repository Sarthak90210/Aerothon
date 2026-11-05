"""Record measured gate-motion recovery and keep the failed flight unchanged."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability';source=root/'logs/reliability_reduced_scope_v29_source_20261008';p=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v28_candidate_20261008/source_manifest.json').read_text());new=json.loads((root/'.scratch/reduced_scope_v29_candidate_20261008/source_manifest.json').read_text())
change=dict(accepted_source=False,added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],removed=[n for n in old if n not in new],thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_transport_queue_s=0.)
(source/'change_from_v28.json').write_text(json.dumps(change,indent=2))
head=f'''# Current checkpoint: V29 provisional

No accepted source. V29 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. All 11 normal-startup module hashes match.
91 focused checks pass, including the actual gate leaf, normal actuator
airframe, streamed lidar keep-out guard and frozen failing observation stream.

V28 closed three trials: field seeds 2 and 3 passed all navigation checks and
actually disarmed. Field 2 retained DEGRADED visual landing quality. Mild
random 3 found its return gate in 15.15 s, versus V27's 187.64 s, but later
timed out at GateAdvance. It recorded two wall contacts and .4034108728140693 m
minimum corridor clearance. Automatic RTL and actual connected disarm were
recorded; the original failed grade is preserved. Two unflown cases were
cancelled, never counted as passes. Its exact-source closed failure review,
recorded setpoints, estimate/truth alignment and original sensor data remain
archived. The contacts occurred during crossing, before the braking phase;
the late phase label did not establish a braking root cause.

The actual gate replay reproduced timeout, wall contact and .4003839764804563 m
clearance with normal .6 s response and zero transport queue. Changing only
the settle-position window did not fix it. Damping the original braking
anchor with measured velocity also did not fix it; neither prototype was
adopted. The successful change confirms signed forward crossing distance
from distinct fresh FCU world-frame ground-velocity captures since speed
admission. It retains the original measured distance, latched heading,
arrival tolerance, fresh pose/velocity/lidar requirements, .08 m/s braking
limit, three distinct braking samples, .3 s settling span and speed ACKs.
Duplicate, pre-admission, backward, sideways, stale, nonfinite and broken
capture histories cannot supply this extra arrival confirmation. The
existing position arrival path and latched streamed setpoint are retained.

The permanent replay regression went RED before the fix and GREEN after it:
crossing/braking completed in 20.8 s, minimum clearance .9145067912135068 m,
zero contact, normal physics. This is a focused diagnostic regression with
recorded estimator error and regenerated scan noise, not rendered or whole
mission qualification. No production node reads the evaluation fixture.

V29 now reruns five exact-source targeted cases, beginning with mild random 3
and field 2. Only all five passes unlock one final offline suite, five native
22/22 acceptance runs and 96 eligible campaign flights. Reduced scope remains
120 selected, 80 weather exclusions and 24 negative geometry classifications.
No campaign flight has qualified. Strong gusts and artificially delayed
control remain unresolved, preserved and excluded. No original 200-case
qualification is claimed. All acceptance limits and thin-obstacle filtering
remain unchanged.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V29 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V28 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |','| V28 mild random 3 | Return search 15.15 s, then gate-crossing timeout and two wall contacts; corridor .4034108728140693 m; automatic RTL and actual disarm | FAIL preserved; two unflown cases cancelled; V29 ground-motion arrival still unaccepted |\n| Strong gust/delayed control |',1)
f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V29 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V29 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v29_targeted_20261008'];index['active_trial']=index['active_runs'][0];index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v29_source_20261008/planned_geometry_scope.json'
index['verification']['v28_closed_failure_review']='logs/reliability_reduced_scope_v28_source_20261008/targeted_failure_closed_review.json'
index['verification']['v29_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v29_source_20261008/installed_startup_imports.json',red='logs/reliability_gate_motion_physics_red_20261008.log',focused='logs/reliability_v29_gate_motion_focused_20261008.log',checks=91,accepted=False)
index['verification']['v28_gate_trace_diagnosis']='logs/reliability_reduced_v28_targeted_20261008/my_world_random_s3/gate_trace_diagnosis.json'
index['verification']['v29_gate_motion_diagnostic']='logs/reliability_gate_motion_arrival_probe_20261008.json'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
 with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write('\n08 October V29: V28 field 2/3 navigation PASS and actual disarm; mild random 3 return search improved to 15.15 s but gate-crossing timeout/contact FAIL, .4034108728140693 m corridor clearance; two wall contacts, RTL and actual disarm retained; two unflown cancelled. Actual gate/normal physics/streamed guard regression reproduced crossing contact. Fresh signed FCU displacement confirmation retains distance, heading, tolerance, freshness, ACKs and braking limits. 20.8 s replay PASS .9145067912135068 m zero contact; 91 focused checks and 11 startup hashes match 938-file freeze. Rejected settle-window/damping probes archived, not adopted. Five targeted cases rerun; all native/campaign qualification pending.\n')
print(json.dumps(change))
