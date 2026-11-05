"""Archive V21 failures and describe the new candidate without accepting it."""
import hashlib,json,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
v21=root/'logs/reliability_reduced_scope_v21_source_20261008'
old=json.loads((root/'.scratch/reduced_scope_v21_candidate_20261008/source_manifest.json').read_text())
old_prov=json.loads((v21/'provenance.json').read_text())
assert hashlib.sha256((v21/'frozen_source.zip').read_bytes()).hexdigest()==old_prov['archive_sha256']
with zipfile.ZipFile(v21/'frozen_source.zip') as z:
    assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in old.items())
batch=json.loads((v21/'interrupted_batch_closed_review.json').read_text())
for r in batch['results']:
    path=root/'logs/reliability_reduced_v21_targeted_20261008'/r['run']
    assert json.loads((path/'source_manifest.json').read_text())==old
source=root/'logs/reliability_reduced_scope_v22_source_20261008'
prov=json.loads((source/'provenance.json').read_text())
new=json.loads((root/'.scratch/reduced_scope_v22_candidate_20261008/source_manifest.json').read_text())
baseline=json.loads((root/'.scratch/reduced_scope_v20_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=[n for n in new if n not in baseline],changed=[n for n in new if n in baseline and new[n]!=baseline[n]],
    removed=[n for n in baseline if n not in new],accepted_source=False,
    trust_age_s=.30,pause_limit_s=.30,thresholds_unchanged=True,lidar_filter_unchanged=True,normal_actuators_unchanged=True)
(source/'change_from_v20.json').write_text(json.dumps(changes,indent=2))
headline=f'''# Current checkpoint: V22 provisional

No accepted source. V22 freezes {len(new)} controlled files, archive SHA256
{prov['archive_sha256']}.
All 11 normal-startup imports match. 287 focused checks pass. V21's early-orbit
change was rejected after flight results and removed from this candidate.
V22 keeps all twelve initial search headings, then tries the existing bounded
guarded orbit before repeating a full sweep if that first sweep observed a
stable, whole, fresh non-outbound green lead. Green is observation geometry,
never identity or crossing permission. Empty/invalid leads retain normal search.

Gate crossing still requires pose, velocity and lidar age at most .30 s and
the same .08 m/s braking threshold and distinct-sample confirmation. A transient
capture gap commands only a hold, resets settling evidence, and allows .30 s
to recover before failing. It cannot cross or hand over on stale observations.
Normal timing/actuator behavior, camera/perception and lidar filters are unchanged.

Five two-worker exact-source targeted trials are running, mild random seed 3
and field seed 2 first. One final offline suite, all five native rendered
acceptances and 96 eligible campaign flights remain gated. Reduced scope is
120 selected, 24 negative geometry classifications and 80 weather exclusions.
No original 200-case qualification is claimed. Strong gusts and artificial
control delay remain unresolved and excluded.

## V21 rejected and interrupted batch

Field seed 1 passed navigation. Field seed 2 failed return after a .31-.37 s
recorded lidar-age interval triggered GateAdvance's immediate stale-data abort.
Mild random seed 3 failed return/time, and field seed 3 failed time. Those four
actually disarmed and their original grades remain failed where applicable.
Mild random seed 4's process was interrupted with last telemetry armed at
606.01 s; final disarm and final grade are unverified. The WSL simulator owning
processes were absent and WSL uptime reset on inspection. The partial batch is
not a completed qualification. Source/run manifests and archive are verified;
all telemetry and original stderr remain in the closed interrupted-batch review.

The landing probe using the recorded initial home reference and return pose
passed before any new landing change, achieving visual lock in 9.8 s. It is
a fixture diagnostic with regenerated random streams and no ROS delivery;
it does not reproduce the field seed 2 timeout or qualify landing.

'''
for name in ['status.md','evidence_report_20261007.md']:
    p=base/name;s=p.read_text(encoding='utf-8')
    if '# Current checkpoint: V22 provisional' not in s:p.write_text(headline+s,encoding='utf-8')
p=base/'evidence_report_20261007.md';s=p.read_text(encoding='utf-8')
s=s.replace('Finish the five targeted navigation cases and final offline suite on V21, then','Finish the five targeted navigation cases and final offline suite on V22, then')
if '| V21 field 2 |' not in s:s=s.replace('| Strong gust/delayed control |',
    '| V21 field 2 | Gate timestamp failure; failed return/mode/ceiling; actual disarm | Preserved failure; bounded hold seam reproduced |\n'
    '| V21 field 3 and mild random 3 | Time failure; mild seed 3 also failed return; actual disarm | Preserved failures; early-orbit candidate rejected |\n'
    '| V21 mild random 4 | Simulator interrupted with last telemetry armed at 606.01 s | Final disarm and grade unverified; never counted as a pass |\n'
    '| Strong gust/delayed control |',1)
p.write_text(s,encoding='utf-8')
p=base/'evidence_index_20261007.json';index=json.loads(p.read_text())
index['current_continuation']=dict(source='V22 provisional',source_files=len(new),archive_sha256=prov['archive_sha256'],remaining='Five targeted trials, one final offline suite, five native rendered acceptances and 96 eligible campaign flights')
index['active_runs']=['logs/reliability_reduced_v22_targeted_20261008'];index['active_trial']='logs/reliability_reduced_v22_targeted_20261008'
index['accepted_source']=None;index['qualification_complete']=False
index['reduced_scope']['classification_audit']='logs/reliability_reduced_scope_v22_source_20261008/planned_geometry_scope.json'
index.setdefault('verification',{})['v21_interrupted_batch']=dict(path=str((v21/'interrupted_batch_closed_review.json').relative_to(root)),source_verified=True,accepted=False,final_case_disarm_verified=False)
index['verification']['v22_startup_and_focused']=dict(startup='logs/reliability_reduced_scope_v22_source_20261008/installed_startup_imports.json',
    gate_red='logs/reliability_gate_capture_pause_red_20261008.log',search_red='logs/reliability_v22_first_sweep_lead_red_20261008.log',focused='logs/reliability_v22_final_focused_20261008.log',checks=287,accepted=False)
p.write_text(json.dumps(index,indent=2),encoding='utf-8')
for name in ['08-rendered-return-clearance.md','37-search-overlapping-exclusion-escape.md']:
    with (base/'issues'/name).open('a',encoding='utf-8') as f:
        f.write('\n08 October V22 continuation: V21 early-orbit candidate rejected after retained failures. Four cases actually disarmed; mild random 4 simulator ended with last telemetry armed, so final disarm is unverified. V22 retains the full initial search sweep before using stable whole-region observations for an existing guarded orbit, and pauses transient gate capture gaps with unchanged .30 s freshness/.08 m/s braking thresholds. Actual-leaf reds and 287 focused greens archived; 11 startup imports match. Five same-source trials active; final acceptance remains open.\n')
print(json.dumps(changes,indent=2))
