"""Publish closed failures and the unaccepted orbit-view recovery candidate."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v28_source_20261008';p=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v27_candidate_20261008/source_manifest.json').read_text());new=json.loads((root/'.scratch/reduced_scope_v28_candidate_20261008/source_manifest.json').read_text())
change=dict(accepted_source=False,added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],removed=[n for n in old if n not in new],thresholds_unchanged=True,thin_obstacles_preserved=True,actuator_response_unchanged=True)
(source/'change_from_v27.json').write_text(json.dumps(change,indent=2))
head=f'''# Current checkpoint: V28 provisional

No accepted source. V28 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. All 11 normal-startup imports match. The return-camera
restart seam and 92 related focused checks pass.

V26 closed with four navigation passes and one failure. Field seeds 1, 2 and 3
and mild random 4 passed navigation and actually disarmed. Mild random 3
failed the high-return altitude handover; automatic RTL and actual disarm
were retained. V27 closed with field seed 2 navigation PASS, corridor minimum
.7354888194818544 m and actual disarm. Mild random 3 found its delivery QR,
completed the stricter climb and entered return search. Search took 187.64 s;
the flight exceeded the unchanged 900 s limit before completing the return.
The safety watcher requested RTL, and actual connected disarm was recorded.
Zero contact and fence events were recorded in both closed V27 trials.
Three unflown cases were cancelled, never counted as passes. Both candidates'
original grades, configurations, source archives and complete file hashes
are retained in their targeted_failure_closed_review.json files.

The actual FindReturnBanner state machine reproduced a missed first orbit
view carrying its final BANNER camera tilt and exhausted second-look flag
into later orbit vantages. V28 starts each orbit vantage at FORWARD, resets
its second BANNER look, and starts a fresh heading dwell. The existing orbit
altitude, bounded speed, fence/red-ground/lidar guards and identity/range
checks remain unchanged. Captured-geometry projection showed readable level
views at later recorded orbit positions, while a 2 m raise did not repair
the early incidence-limited view. These are diagnostic replays, not rendered
qualification or a reconstruction of every runtime detector callback.

The initial focused fixture lacked the speed acknowledgement stub; that
fixture was corrected without changing production speed behavior. A premature
V28 freeze is retained under the explicitly named preverification directories;
it ran no flights and cannot qualify. The final V28 freeze is the hash above.

Five same-source targeted passes still gate one final offline suite, five
native 22/22 rendered acceptances, and 96 eligible campaign flights. The exact
reduced matrix remains 120 selected cases, 80 weather exclusions, and 24
negative geometry classifications. No campaign flight has qualified. Strong
gust and artificially delayed-control failures remain unresolved and excluded.
No original 200-case qualification is claimed. V28 retains the strict return
climb and zero-disturbance certificate; all .70 m corridor and other required
acceptance limits remain unchanged.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V28 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V27 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |','| V27 mild random 3 | QR found and strict climb complete; return search 187.64 s; 900 s limit exceeded, watcher RTL, actual disarm | FAIL preserved; three unflown cases cancelled; camera state leak reproduced and V28 still unaccepted |\n| Strong gust/delayed control |',1)
f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V28 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V28 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v28_targeted_20261008'];index['active_trial']=index['active_runs'][0];index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v28_source_20261008/planned_geometry_scope.json'
for v in ['v26','v27']:index['verification'][v+'_closed_failure_review']=f'logs/reliability_reduced_scope_{v}_source_20261008/targeted_failure_closed_review.json'
index['verification']['v28_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v28_source_20261008/installed_startup_imports.json',red='logs/reliability_orbit_camera_restart_red_20261008.log',focused='logs/reliability_v28_orbit_camera_focused_20261008.log',checks=93,accepted=False)
index['verification']['v27_projection_diagnosis']='logs/reliability_reduced_v27_targeted_20261008/my_world_random_s3/orbit_camera_projection_diagnosis.json'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
 with (base/'issues'/name).open('a',encoding='utf-8') as f:f.write('\n08 October V28: V26 closed four navigation passes/one failed altitude handover. V27 closed field 2 navigation PASS .7354888194818544 m corridor clearance, mild random 3 search/time FAIL; both actual disarm, zero contact/fence; three unflown cancelled. Original failure reviews retained. Actual orbit search seam RED showed camera tilt and exhausted second look leaking to later vantages. V28 restarts each guarded orbit view level with its own second look/fresh dwell; altitude, speed, guards and thresholds unchanged. 93 focused PASS, 11 startup imports, 935-file final freeze. All targeted/native/campaign qualification remains pending.\n')
print(json.dumps(change))
