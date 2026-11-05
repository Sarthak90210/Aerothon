"""Record the exact provisional speed lease source and outstanding gates."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v23_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v22_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v23_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in old],changed=[n for n in new if n in old and new[n]!=old[n]],
    removed=[n for n in old if n not in new],accepted_source=False,thresholds_unchanged=True,
    lidar_filter_unchanged=True,normal_actuators_unchanged=True,search_pacing_unchanged=True)
(source/'change_from_v22.json').write_text(json.dumps(changes,indent=2))
headline=f'''# Current checkpoint: V23 provisional

No accepted source. V23 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match; 272 focused checks pass. The actual normal
mission sequence failed the regression: a .65 m/s admitted search cap persisted
into the high return transit. Retained V22 mild seed 3 measurements show the
same pattern with a .60 m/s cap: 41.70 m horizontal travel took 70.64 seconds,
mean .590 m/s and median recorded velocity .600 m/s.

V23 records the previously admitted navigation cap before search. Only after
delivery, return climb and confirmed nadir camera, a new stage holds position
until the FCU acknowledges restoration bounded by that previous cap and the
existing configured navigation ceiling. Fresh pose, high altitude and camera
prerequisites are mandatory. Rejection, unavailable service and timeout fail
safely. Search pacing, .30 s capture freshness, .08 m/s braking, all acceptance
thresholds, sensors, lidar filtering and actuator physics remain unchanged.

The V23 pipeline is queued behind the final V22 trial. Its five two-worker
same-source targeted trials must pass before one final offline suite, five
full native rendered acceptances and 96 eligible campaign flights. Reduced
scope remains 120 selected, 24 negative geometry classifications and 80 weather
exclusions. Strong gusts and artificial control delay remain unresolved and
excluded. Original 200-case qualification is not claimed.

V22 fields 1, 2 and 3 have completed and actually disarmed. Field seed 2 passed
all navigation checks with precise landing, .730684650 m corridor clearance,
757.4 airborne seconds and .32 m home distance. Mild random seed 3 failed
return/time despite zero contacts/fence breaches and .732488875 m corridor
clearance; its original watchdog RTL and actual disarm remain preserved.
Final mild seed 4 is still active. V22 cannot qualify and no full suite is run
on it. Its flights use the isolated V22 snapshot while ROOT now matches V23.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V23 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
s=s.replace('Finish the five targeted navigation cases and final offline suite on V22, then','Finish the five targeted navigation cases and final offline suite on V23, then')
if '| V22 mild random 3 |' not in s:s=s.replace('| Strong gust/delayed control |',
    '| V22 mild random 3 | QR found at 746.99 s; failed return/time; watchdog RTL and actual disarm; zero contacts/fence | Preserved failure; search speed lease leak reproduced in actual tree |\n| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V23 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='V22 closure, five V23 targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v22_targeted_20261008'];index['active_trial']='logs/reliability_reduced_v22_targeted_20261008'
index['queued_trial']='logs/reliability_reduced_v23_targeted_20261008';index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v23_source_20261008/planned_geometry_scope.json'
index.setdefault('verification',{})['v23_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v23_source_20261008/installed_startup_imports.json',
    red='logs/reliability_return_speed_lease_red_20261008.log',focused='logs/reliability_v23_navigation_speed_focused_20261008.log',checks=272,accepted=False)
index['verification']['v22_mild_3_speed_lease_diagnosis']='logs/reliability_reduced_v22_targeted_20261008/my_world_random_s3/return_speed_lease_diagnosis.json'
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:
        f.write('\n08 October V23 continuation: V22 field seeds 1/2/3 actually disarmed; field 2 passed navigation with precise landing. Mild random 3 failed time/return, preserving actual RTL/disarm. Its 41.70 m high return leg took 70.64 s at retained .60 m/s search cap. The actual built-tree lease regression failed. V23 restores a bounded prior navigation cap only after high-altitude/nadir/fresh-pose prerequisites and FCU acknowledgement. 272 focused checks and 11 startup imports match the freeze. New trials queued after final V22 disarm; no native/campaign acceptance yet.\n')
print(json.dumps(changes,indent=2))
