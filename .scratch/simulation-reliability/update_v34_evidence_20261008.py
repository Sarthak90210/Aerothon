"""Record V33 safely closed camera failure separately from provisional V34."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v34_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v34_candidate_20261008/source_manifest.json').read_text())
old=json.loads((root/'.scratch/reduced_scope_v33_candidate_20261008/source_manifest.json').read_text())
p=json.loads((source/'provenance.json').read_text())
changed=[n for n in new if n in old and new[n]!=old[n]];added=[n for n in new if n not in old]
assert changed==['src/aerothon_mission/mission_bt/mission_bt/mission_tree.py'],changed
assert added==['sim/test_return_camera_handoff.py'],added
(source/'change_from_v33.json').write_text(json.dumps(dict(accepted_source=False,changed=changed,added=added,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_response_s=.6,extra_queue_s=0.),indent=2))
review=json.loads((root/'logs/reliability_reduced_scope_v33_source_20261008/targeted_failure_closed_review.json').read_text())
assert not review['pass_navigation'] and len(review['results'])==5
head=f'''# Current checkpoint: V34 provisional, return camera handoff verification

V34 freezes {len(new)} controlled files, archive SHA256
{p['archive_sha256']}. 59 focused normal-startup camera,
framing, gate-motion, corridor registration and return-climb checks pass.
The actual built return handoff went RED at the inherited -10 degree search
tilt before the change. It now restores BANNER and waits for measured camera
settlement before alignment. Existing timeout and low-view level-camera
retry remain unchanged. Stale readback, wrong measured angle and timeout
controls pass. No movement is authorized by camera framing.

V33 safely closed five targeted trials: four navigation passes, one failure.
Field seed 3 found the delivery QR and return gate, then failed alignment
after seven vantages. A custom camera tilt from distant search remained
active after the approach; subsequent clipped/missing lettering led to
230 seconds of alignment and eventual safe return. The actual connected
disarm, failure grade, zero contacts/fence breaches, source archive,
configurations and every recording/telemetry hash are retained in the closed
review. Field 1/2 and mild random 3/4 passed navigation. Random 4 retains
DEGRADED landing quality. No offline, native or campaign ran on V33.

Field 3 reruns first in parallel with mild random 3. All five exact-source
targeted passes remain required before the complete reduced-scope offline
suite, five native 22/22 acceptances and 96 eligible campaign flights.
The five strong-gust positive offline flight tests remain explicitly
excluded, with their original V32 failures preserved. Three empty photograph
corpus checks remain skipped. Neither exclusion counts as a pass.
Strong gusts and artificially delayed control remain unresolved/excluded.
The reduced campaign has 120 selected entries, 80 weather exclusions and
24 negative geometry classifications. No accepted source or original
200-case qualification is claimed. Thin obstacles and all acceptance
thresholds remain unchanged.

'''
for name in ('status.md','evidence_report_20261007.md'):
    f=base/name;s=f.read_text(encoding='utf-8')
    if '# Current checkpoint: V34 provisional' not in s:f.write_text(head+s,encoding='utf-8')
f=base/'evidence_report_20261007.md';s=f.read_text(encoding='utf-8')
if '| V33 field 3 |' not in s:
    s=s.replace('| Strong gust/delayed control |','| V33 field 3 | Delivery QR and return gate found; alignment lost lettering at inherited custom camera tilt after approach, failed seven vantages; safe return and actual disarm, zero contacts/fence breaches; other four targeted navigation cases passed | Original failure preserved; V34 normal-startup camera settlement fix remains unaccepted |\n| Strong gust/delayed control |',1)
    f.write_text(s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text())
index['current_continuation']=dict(source='V34 provisional',source_files=len(new),archive_sha256=p['archive_sha256'],remaining='Five V34 targeted trials, complete reduced-scope offline suite, five rendered acceptances, 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v34_targeted_20261008'];index['active_trial']=index['active_runs'][0]
index['accepted_source']=None;index['qualification_complete']=False
index['verification']['v33_closed_failure_review']='logs/reliability_reduced_scope_v33_source_20261008/targeted_failure_closed_review.json'
index['verification']['v33_return_camera_diagnosis']='logs/reliability_reduced_v33_targeted_20261008/my_world_field_s3/return_banner_handoff_diagnosis.json'
index['verification']['v34_focused']=dict(red='logs/reliability_return_camera_handoff_red_20261008.log',log='logs/reliability_v34_return_handoff_focused_20261008.log',checks=59,accepted=False)
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print('V34 provisional registered; V33 field-3 failure remains preserved')
