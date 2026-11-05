"""Record all failed runtime evidence and explicit real-time configuration."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v37_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v37_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v36_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text());changed=[n for n in new if n in old and new[n]!=old[n]]
assert changed==['src/aerothon_mission/mission_bt/mission_bt/gate_braking.py','sim/test_gate_brake_motion_anchor.py'],changed
assert set(new)==set(old)
review=json.loads((root/'logs/reliability_reduced_scope_v36_source_20261008/targeted_failure_closed_review.json').read_text())
assert len(review['results'])==2 and not review['pass_navigation']
(source/'change_from_v36.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=[],focused_checks=107,thresholds_unchanged=True,lidar_filter_unchanged=True,headless_rtf=1.,headless_workers=2,normal_response_s=.6,extra_queue_s=0.,timer_boundary=dict(limit_ns=300000000,accepted_exact_boundary=True,rejected_plus_one_nanosecond=True),retained_runtime_failures='logs/reliability_reduced_scope_v36_source_20261008/targeted_failure_closed_review.json',records={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['logs/reliability_gate_capture_boundary_red_20261008.log','logs/reliability_v37_integrated_focused_20261008.log','logs/reliability_v36_qualification_pipeline_20261008.log']}),indent=2))
head=f'''# Current checkpoint: V37 provisional, exact-clock guard and real-time flights

V37 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. 107 integrated focused checks pass.
The recorded 682.02 to 682.32 capture interval reproduces a false gate
history-gap rejection from floating-point subtraction. The gap comparison
now uses the ROS clock's integer nanosecond precision: exactly 300000000 ns
is accepted, 300000001 ns is rejected at three different clock epochs.
The 0.30 s threshold is unchanged. Specific vector-history faults are now
recorded in gate failure reasons. Prior gate braking, camera handoff,
search braking, scan registration and physical altitude fixes are retained.

V36 safely closed two failed mild-weather flights; three queued field cases
were never flown. Random 4 failed its gate motion guard, then contacted
the board during abort and eventually disarmed. Random 3 experienced
computation-deadline misses and a genuine vertical-motion capture gap;
it stopped in return corridor, exceeded 900 s, then returned on battery
abort and actually disarmed. The operator stop watchdog subprocess timed
out after 15 host seconds and terminated; this limitation is retained in
the pipeline log. No older failure is excluded or upgraded to a pass.
The recordings demonstrate delayed arrivals on this accelerated host run;
they do not establish a callback race or prove the numerical boundary was
the sole cause of the actual gate failure. Immutable source/configuration,
every failed grade, contact and actual disarm are in the closed review.
No complete offline, native or campaign qualification ran on V36.

V37 object flights use real-time simulation speed, RTF 1, with two workers.
Controller and sensor rates in simulated time, the 0.20 s computation
budget, 0.6 s normal actuator response, zero additional transport queue and
all acceptance thresholds remain unchanged. This reduces host work per
second without adding control delay. Targeted and campaign verifiers
require this exact configuration. The watchdog records timeout attempts
and retries instead of exiting and leaving later stop requests unhandled.

All five normal-timing targeted passes, the complete reduced-scope offline
suite, five native 22/22 acceptances and 96 eligible campaign flights remain
required on the final source. Strong gusts and artificial delayed control
remain unresolved and excluded. No accepted source or original 200-case
qualification is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V37 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V36 mild random 3/4 |' not in s:
    s=s.replace('| Strong gust/delayed control |','| V36 mild random 3/4 | Random 4 gate history guard failed, board contact during abort, actual disarm; random 3 deadlines/capture gap, return stopped, flight over 900 s, battery return and actual disarm; stop watchdog timed out | Both failures preserved; three queued cases unflown; V37 remains unaccepted |\n| Strong gust/delayed control |',1)
    f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V37 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],headless_rtf=1.,remaining='Five V37 targeted trials, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v37_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v36_closed_failure_review']='logs/reliability_reduced_scope_v36_source_20261008/targeted_failure_closed_review.json'
index['verification']['v37_focused']=dict(log='logs/reliability_v37_integrated_focused_20261008.log',checks=107,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V37 unaccepted candidate with explicit real-time configuration; all V36 failures preserved')
