"""Record safely closed V34 failure and unaccepted V35 integrated candidate."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v35_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v35_candidate_20261008/source_manifest.json').read_text(encoding='utf-8'))
old=json.loads((root/'.scratch/reduced_scope_v34_candidate_20261008/source_manifest.json').read_text(encoding='utf-8'))
provenance=json.loads((source/'provenance.json').read_text(encoding='utf-8'))
changed=[n for n in new if n in old and new[n]!=old[n]];added=[n for n in new if n not in old]
assert changed==['src/aerothon_mission/mission_bt/mission_bt/gate_braking.py','sim/test_gate_braking.py','sim/test_gate_capture_pause.py','sim/test_gate_motion_physics.py'],changed
assert set(added)=={'sim/test_gate_brake_motion_anchor.py','sim/fixtures/gate_brake_mild_s3_20261008.json'},added
(source/'change_from_v34.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=added,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_queue_s=0.,regression_count=66,diagnostic_replay_limitations='Recorded estimator error interpolated; wind and scan corruption regenerated, ROS arrivals not reconstructed',diagnostic_records={name:dict(sha256=hashlib.sha256((root/name).read_bytes()).hexdigest()) for name in ['logs/reliability_v34_gate_brake_causes_20261008.log','logs/reliability_v34_gate_brake_causes_20261008.json','logs/reliability_v35_integrated_focused_20261008.log']}),indent=2))
review=json.loads((root/'logs/reliability_reduced_scope_v34_source_20261008/targeted_failure_closed_review.json').read_text(encoding='utf-8'))
assert not review['pass_navigation'] and len(review['results'])==3
head=f'''# Current checkpoint: V35 provisional, gate physical braking hold verification

V35 freezes {len(new)} controlled files, archive SHA256
{provenance['archive_sha256']}. 66 integrated focused checks pass.
The existing recorded entry replay retains 0.913 m clearance; the new
recorded braking seam changes from 0.668 m failure to 0.986 m pass with
normal 0.6 s actuator response and zero additional control queue. A fixed
estimated XY hold chased GPS changes. The new estimated-frame anchor
cancels those changes while preserving the physical arrival from distinct
continuous FCU ground velocities. Missing, malformed, nonfinite, future or
gapped vectors fail closed. Duplicate captures cannot finish braking.
Pending speed acknowledgement remains a physical hold. Altitude, freshness,
speed, settling and clearance thresholds and the lidar filter are unchanged.
These replays regenerate wind and lidar; they are diagnostic evidence,
not reconstructed ROS scheduling or rendered qualification.

V34 safely closed three trials: field seeds 2 and 3 passed navigation and
landed precisely; mild random seed 3 failed only corridor clearance at
0.6560762476749438 m, with zero contacts/fence breaches and actual disarm.
The minimum occurred during gate crossing/braking before the corridor
velocity controller was enabled. The full old failure, source, configuration
and telemetry hashes are preserved. Two queued flights were cancelled
before flight. No offline, native or campaign qualification ran on V34.

V35 runs mild random 3 first alongside field 3, then field 2/1 and mild
random 4. Five exact-source navigation passes are required before the
complete reduced-scope offline suite, five native 22/22 acceptances and
96 eligible campaign flights. Strong gusts and artificial delayed control
remain unresolved and excluded; no original 200-case qualification or
accepted final source is claimed.

'''
for name in ['status.md','evidence_report_20261007.md']:
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V35 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V34 mild random 3 |' not in s:
    s=s.replace('| Strong gust/delayed control |','| V34 mild random 3 | Corridor clearance 0.656 m during gate crossing/braking, zero contacts/fence breaches, actual disarm; field 2/3 navigation passed; two unflown cases cancelled | Original failure preserved; V35 physical braking hold remains unaccepted |\n| Strong gust/delayed control |',1)
    f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['current_continuation']=dict(source='V35 provisional',source_files=len(new),archive_sha256=provenance['archive_sha256'],remaining='Five V35 targeted trials, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v35_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v34_closed_failure_review']='logs/reliability_reduced_scope_v34_source_20261008/targeted_failure_closed_review.json'
index['verification']['v35_focused']=dict(log='logs/reliability_v35_integrated_focused_20261008.log',checks=66,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V35 unaccepted source registered; safely disarmed V34 failure preserved')
