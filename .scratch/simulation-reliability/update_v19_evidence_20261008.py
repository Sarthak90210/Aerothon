"""Keep the working evidence explicit while the candidate remains unaccepted."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
source=root/'logs/reliability_reduced_scope_v19_source_20261008'
provenance=json.loads((source/'provenance.json').read_text())
sha=provenance['archive_sha256']
old=json.loads((root/'.scratch/reduced_scope_v18_candidate_20261008/source_manifest.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v19_candidate_20261008/source_manifest.json').read_text())
change=dict(added=[n for n in new if n not in old],removed=[n for n in old if n not in new],
    changed=[n for n in new if n in old and new[n]!=old[n]],thresholds_unchanged=True,
    normal_timing_unchanged=True,lidar_filter_unchanged=True,accepted_source=False)
(source/'change_from_v18.json').write_text(json.dumps(change,indent=2))
headline=f'''# Current checkpoint — V19 provisional

No accepted source. Frozen {len(new)} controlled files; archive SHA256
{sha}.
Normal startup imports match the freeze for all 11 checked modules. Return
framing now consumes four distinct fresh identified horizontally clipped
captures during yaw settlement and uses the existing 2 m backoff, shared
maximum of two attempts. Accepted board range, plane, crossing permission,
camera tilt requirements and every acceptance threshold are unchanged.
The actual leaf regression failed before the fix; 92 focused return/gate,
capture and clearance checks pass. Further integrated checks are in progress.
V18 closed 4/5 normal-timing navigation cases: fields 1/2/3 and mild random 4
pass; mild random 3 fails return/time and was safely stopped with operator RTL.
Every case has actual connected disarm, no contacts and no fence breaches.
V18 is not accepted. Its LAND model correction retains estimated-position
control, as the installed ArduPilot source does; physical response, wind,
normal callbacks and zero added queue are unchanged.
V19 targeted trials, final offline suite, all five rendered acceptances and
96 eligible campaign flights remain pending. Prior-source passes are not
reused as V19 qualification. 120 selected entries include 24 negative geometry
classifications; 80 weather entries are excluded. The original 200-case
qualification is not claimed. Strong gusts and artificial delay remain
unresolved and excluded. All failures and recordings remain preserved.

'''
status=base/'status.md';text=status.read_text(encoding='utf-8')
if not text.startswith('# Current checkpoint — V19 provisional'):
    status.write_text(headline+'## Prior checkpoints\n\n'+text,encoding='utf-8')
report=base/'evidence_report_20261007.md';text=report.read_text(encoding='utf-8')
newsection=f'''## Current provisional V19

Frozen source: {len(new)} files, archive SHA256 `{sha}`. Accepted source remains
**none**. The 11 normal-startup imports match this freeze. The new return
framing correction passed 92 focused checks and is not yet mission-qualified.
`logs/reliability_reduced_scope_v19_source_20261008/change_from_v18.json`
records the controller change and the added regression file.

V18's normal-timing two-worker probe closed 4/5 navigation cases. Fields 1/2/3
passed with corridor clearances .741351961/.716641203/.729317782 m and airborne
times 780.3/776.9/777.8 s. Mild random 4 passed; mild random 3 failed return/time.
Its operator RTL, actual disarm and unchanged failed grade are preserved.
Full object-fixture payload grades remain unqualified, not motor-delivery passes.
`logs/reliability_reduced_scope_v18_source_20261008/targeted_failure_closed_review.json`
contains configurations, source identities, per-artifact hashes and disarms.

The normal LAND model now latches estimated XY and retains horizontal position
control, matching the installed ArduPilot implementation. The actual closed-loop
seam reproduced 1.2705 m wind drift before the correction; 69 focused model and
recording checks pass. The upstream source review and hashes are archived in
`logs/reliability_land_model_primary_source_20261008/primary_source_review.json`.
This remains an object model, not a replacement for native rendered acceptance.

V17's lower-load retry closed 1/3 navigation cases: field 3 passed; field 1
failed home landing at 1.54 m; mild random 3 failed return/time. All disarmed.
The latter recorded 15 distinct identified horizontally clipped return views
during alignment. These passive snapshots do not establish the full 20 Hz
capture history; the actual-leaf regression supplies the repeatable failing seam.
Diagnosis: `logs/reliability_reduced_v17_normal_timing_retry_20261008/my_world_random_s3/return_width_framing_diagnosis.json`.
Closed review: `logs/reliability_reduced_scope_v17_source_20261008/normal_timing_retry_closed_review.json`.

V19 has no final offline, rendered or campaign passes yet. All five full native
acceptances and the 96-flight matrix remain gated. Every previous failure remains
listed below; older passes are source-specific and are not final qualification.

## Prior provisional V17

'''
marker='The active provisional source is V17:'
if '## Current provisional V19' not in text:
    text=text.replace(marker,newsection+'The prior provisional source is V17:',1)
    text=text.replace('failed cases are under a same-source/configuration probe with two workers\nafter the full offline suite finished.',
                      'failed cases were probed with two workers after the full offline suite finished;\nthat retry closed 1/3 navigation passes, as recorded above.')
    report.write_text(text,encoding='utf-8')
path=base/'evidence_index_20261007.json';idx=json.loads(path.read_text(encoding='utf-8'))
idx['current_continuation']=dict(source='V19 provisional',source_files=len(new),archive_sha256=sha,
    remaining='V19 focused regressions and targeted cases; final offline; five full rendered acceptances; 96 eligible campaign flights')
idx['active_runs']=[]
idx['verification'].update(
    v17_normal_timing_retry_closed_review='logs/reliability_reduced_scope_v17_source_20261008/normal_timing_retry_closed_review.json',
    v17_return_width_diagnosis='logs/reliability_reduced_v17_normal_timing_retry_20261008/my_world_random_s3/return_width_framing_diagnosis.json',
    v18_targeted_failure_closed_review='logs/reliability_reduced_scope_v18_source_20261008/targeted_failure_closed_review.json',
    v18_land_model_primary_source='logs/reliability_land_model_primary_source_20261008/primary_source_review.json',
    v19_installed_startup='logs/reliability_reduced_scope_v19_source_20261008/installed_startup_imports.json',
    v19_return_focused='logs/reliability_v19_return_focused_20261008.log')
idx['accepted_source']=None;idx['qualification_complete']=False;idx['campaign_200_qualified']=False
path.write_text(json.dumps(idx,indent=2),encoding='utf-8')
print(json.dumps(change))
