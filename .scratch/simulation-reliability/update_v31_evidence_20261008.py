"""Keep V30 failed clearance and rejected reserve separate from V31 evidence."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v31_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v31_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v30_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text())
(source/'change_from_v30.json').write_text(json.dumps(dict(accepted_source=False,changed=[n for n in new if n in old and new[n]!=old[n]],added=[n for n in new if n not in old],thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_queue_s=0.),indent=2))
head=f'''# Current checkpoint: V31 provisional, scan-motion verification active

V31 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. 51 focused capture/controller/landing/gate checks pass;
80 further controller, scan geometry, velocity timing and command regressions
pass. These batches overlap and are not summed as unique tests.

V30 closed three targeted trials. Field seeds 2 and 3 passed all navigation
checks and actually disarmed with PRECISE visual landing quality. Landing took
about 24 seconds on each. Mild random seed 3 landed and disarmed within the
900-second limit, but failed corridor clearance at .6908234714203971 m.
All three had zero contacts and zero fence breaches. Two unflown cases were
cancelled. Original grades, source hashes and actual disarms are retained in
the exact-source closed review. No offline suite, native or campaign was run.

At the failed clearance minimum, recorded observed clearance .7289959824800055
m exceeded independently measured truth .6908234714203971 m by about 38 mm.
Subscription timing prevents treating the two captures as exactly simultaneous.
The actual scan registration and packet/normal-airframe regression reproduces
clearance .6920706531937814 m when stationary ground velocity is accompanied
by 40 mm GPS position jitter. Scan alignment previously treated that GPS jitter
as short aircraft displacement, shifting obstacle points away from the aircraft.

V31 uses distinct fresh FCU world ground-velocity captures to integrate the
short displacement between scan capture and current pose. Broken, stale or
uncovered histories fail closed; at most .06 s of last-sample continuation is
allowed for normal pose/velocity callback skew. Capture orientation, relative
sensor mount, all original ranges, thin obstacles, filters, motion budget,
actuator response and acceptance thresholds remain unchanged. Existing paired
pose fallback is retained when no FCU velocity stream exists.

The actual registration/packet regression went RED before this fix and GREEN
after it. The recorded-entry corridor replay reaches 10.34 m progress in 22.5
s, .72650807605208 m minimum clearance, zero contacts. It regenerates lidar
and does not reconstruct ROS callback ordering or qualify a whole mission.
The earlier 50 mm reserve prototype fixed the narrow range-error seam but got
stuck in the recorded corridor at 2.93 m progress. It was rejected and was
never integrated into production.

Five targeted cases now rerun. All five passes are required before one final
offline suite, five rendered 22/22 acceptances and 96 eligible campaign flights.
No accepted source exists. Strong gusts and artificially delayed control remain
unresolved, preserved and excluded. The reduced matrix retains 120 selected
entries, 80 weather exclusions and 24 negative geometry classifications.
No original 200-case qualification is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '# Current checkpoint: V31 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V30 mild random 3 |' not in s:
 s=s.replace('| Strong gust/delayed control |','| V30 mild random 3 | Actual disarm within 900 s, but corridor clearance .6908234714203971 m; zero contacts/fence breaches; field 2 and 3 navigation PASS with PRECISE landing, two unflown cancelled | FAIL retained; simple reserve prototype rejected for STUCK; V31 scan-motion alignment still unaccepted |\n| Strong gust/delayed control |',1)
 f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V31 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V31 targeted trials, final offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v31_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v30_closed_failure_review']='logs/reliability_reduced_scope_v30_source_20261008/targeted_failure_closed_review.json'
index['verification']['v31_focused']=dict(red='logs/reliability_scan_pose_noise_physics_red_20261008.log',focused=['logs/reliability_v31_scan_motion_focused_20261008.log','logs/reliability_v31_controller_focused_20261008.log'],batch_checks=[51,80],overlap=True,accepted=False)
index['verification']['v31_corridor_probe']='logs/reliability_v31_scan_motion_corridor_probe_20261008.json'
index['verification']['rejected_v30_reserve']='logs/reliability_v30_corridor_reserve_probe_20261008.json'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V31 provisional registered, V30 failed clearance and rejected reserve retained')
