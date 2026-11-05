"""Preserve failed height gate separately from unaccepted motion-hold fix."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v36_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v36_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v35_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text());changed=[n for n in new if n in old and new[n]!=old[n]];added=[n for n in new if n not in old]
assert changed==['src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'],changed
assert set(added)=={'sim/test_corridor_vertical_motion.py','sim/test_corridor_vertical_motion_physics.py','sim/fixtures/corridor_return_altitude_mild_s4_20261008.json'},added
(source/'change_from_v35.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=added,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_queue_s=0.,focused_checks=98,diagnostic_limits='Evaluation-only recorded estimator errors; normal airframe vertical publication; horizontal navigation unexercised',records={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['logs/reliability_v35_return_altitude_red_20261008.log','logs/reliability_v35_altitude_causes_20261008.log','logs/reliability_v36_return_altitude_green_20261008.log','logs/reliability_v36_integrated_focused_20261008.log']}),indent=2))
review=json.loads((root/'logs/reliability_reduced_scope_v35_source_20261008/targeted_failure_closed_review.json').read_text());assert len(review['results'])==5 and not review['pass_navigation']
head=f'''# Current checkpoint: V36 provisional, physical corridor altitude hold verification

V36 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. 98 integrated focused checks pass.
The V35 captured barometer errors replay the corridor dip through the actual
published vertical command and unchanged normal airframe: minimum 0.274 m,
below the unchanged 0.30 m airborne floor. With constant barometer errors
the same control passes. Half gain also passes that trace but retains
estimator-driven physical motion; it was not adopted. The new hold uses
signed FCU vertical displacement from the actual control handover while
retaining the commanded altitude offset, original 0.8 gain and 0.6 m/s cap.
The replay minimum becomes 0.784 m. Distinct captures integrate actual
motion; duplicate captures and repeated unchanged target messages cannot
reset the hold. Invalid or discontinuous motion fails closed until an
actual new handover. True sink, target changes, stale/missing/future/nonfinite
captures, disabling and re-enabling controls pass. This isolated vertical
replay is diagnostic evidence; horizontal flight and native delivery are
not exercised by it. No geometric truth or venue configuration is a
production input; lidar filtering and all acceptance limits are unchanged.

V35 safely closed five trials. Field 1/2/3 and mild random 3 passed all
13 navigation checks. Mild random 3 retained 0.7424024489799385 m corridor
clearance and 2.204071263555253 m red clearance, with actual precise disarm.
Mild random 4 failed return traversal when true altitude dipped below 0.30 m
for eight samples despite 0.7339558114779715 m wall clearance. Zero contacts
and fence breaches, actual disarm and DEGRADED landing are retained.
The old failed grade remains failed. No complete offline, native or campaign
qualification ran on V35.

V36 runs mild random 4/3 first, then field 2/1/3 with normal actuator
response and zero added queue. Five exact-source navigation passes remain
required before the complete reduced-scope offline suite, five native
22/22 acceptances and 96 eligible campaign flights. Strong gusts and
artificial delayed control remain unresolved and excluded. No accepted
source or original 200-case qualification is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V36 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V35 mild random 4 |' not in s:
    s=s.replace('| Strong gust/delayed control |','| V35 mild random 4 | Return corridor below 0.30 m floor for eight samples; corridor clearance 0.734 m, zero contacts/fence, actual disarm; DEGRADED landing retained; other four cases passed navigation | Original failed grade preserved; V36 physical vertical hold remains unaccepted |\n| Strong gust/delayed control |',1)
    f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V36 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V36 targeted trials, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v36_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v35_closed_failure_review']='logs/reliability_reduced_scope_v35_source_20261008/targeted_failure_closed_review.json'
index['verification']['v36_focused']=dict(log='logs/reliability_v36_integrated_focused_20261008.log',checks=98,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V36 unaccepted candidate registered; safely disarmed V35 height failure preserved')
