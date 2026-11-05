"""Close the failed native recording and track the recorder-only successor."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from qualification_evidence import recorded_disarm
source=root/'logs/reliability_reduced_scope_v16_source_20261008'
manifest=json.loads((root/'.scratch/reduced_scope_v16_candidate_20261008/source_manifest.json').read_text())
with zipfile.ZipFile(source/'frozen_source.zip') as frozen:
    assert all(hashlib.sha256(frozen.read(p)).hexdigest()==sha for p,sha in manifest.items())
run=root/'logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008'
recorded=json.loads((run/'source_manifest.json').read_text())
assert {p:s for p,s in recorded.items() if p.startswith(('src/','scripts/','sim/'))}==manifest
summary=json.loads((run/'summary.json').read_text());grade=json.loads((run/'grade.json').read_text())
assert summary['acceptance_pass'] is False and grade['pass'] is False
rows=[json.loads(line) for line in (run/'onboard.jsonl').read_text().splitlines()]
disarm=recorded_disarm(rows);assert disarm
diagnosis=json.loads((run/'hook_contact_diagnosis.json').read_text())
assert diagnosis['failure_counts']=={'winch_fresh':18}
assert grade['aircraft_contact_evidence']['valid'] and len(grade['aircraft_contact_evidence']['unexpected_contacts'])==18
review=dict(accepted_source=False,path=str(run.relative_to(root)),source_files=len(manifest),
            source_archive_sha256=json.loads((source/'provenance.json').read_text())['archive_sha256'],
            source_initial_record_and_archive_match=True,source_after_abort_note='Recorder fix prepared after operator RTL request; the already running V16 recorder retained its launched code. Contact grader unchanged.',
            summary=summary,grade=grade,connected_disarm=disarm,operator_stop=json.loads((run/'operator_stop.json').read_text()),
            diagnosis=diagnosis,unresolved_cleanup='Native contact recorder pybind11 GIL shutdown abort after disarm; stderr preserved; recorded contact coverage valid',
            files={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in run.iterdir() if p.is_file()})
closed=source/'rendered_split_failure_closed_review.json'
with closed.open('x') as f:json.dump(review,f,indent=2)
new_source=root/'logs/reliability_reduced_scope_v17_source_20261008'
new=json.loads((root/'.scratch/reduced_scope_v17_candidate_20261008/source_manifest.json').read_text())
changes=dict(added=sorted(set(new)-set(manifest)),removed=sorted(set(manifest)-set(new)),changed=[p for p in manifest if p in new and new[p]!=manifest[p]])
assert changes==dict(added=['sim/test_winch_capture_recording.py'],removed=[],changed=['sim/record_delivery.py'])
(new_source/'change_from_v16.json').write_text(json.dumps(dict(changes=changes,controller_perception_and_contact_grader_unchanged=True),indent=2))
prov=json.loads((new_source/'provenance.json').read_text());base=root/'.scratch/simulation-reliability'
index_path=base/'evidence_index_20261007.json';idx=json.loads(index_path.read_text(encoding='utf-8'))
idx['runs']['V16 split recorder aliasing failure']=dict(path=str(run.relative_to(root)),scope='full rendered; safely interrupted after lost contact qualification',result=summary,closed_review=str(closed.relative_to(root)))
idx['verification'].update(v16_native_failure_closed_review=str(closed.relative_to(root)),v17_native_evidence_components='logs/reliability_v17_native_evidence_components_20261008.log',v17_recorder_red_control='logs/reliability_v17_winch_arrival_red_20261008.log',v17_installed_startup_imports=str((new_source/'installed_startup_imports.json').relative_to(root)))
idx['active_runs']=['logs/reliability_reduced_v17_targeted_20261008','logs/reliability_reduced_v17_full_offline_20261008.log']
idx['current_continuation']=dict(source='V17 provisional',source_files=prov['files'],archive_sha256=prov['archive_sha256'],remaining='Five exact-source targeted cases and final offline suite active; five rendered acceptances and 96 reduced campaign flights pending')
index_path.write_text(json.dumps(idx,indent=2),encoding='utf-8')
status=base/'status.md'
status.write_text(f'''# Current checkpoint — V17 provisional

No accepted source. Frozen {prov['files']} files; archive SHA256
{prov['archive_sha256']}.
Only the passive winch-arrival recording changed from V16, plus nine regression
tests. Controller, perception, contact grader and all thresholds are unchanged.
The actual callback/contact-grader seam reproduced the missed capture before
the fix; 62 focused recording/contact/qualification checks pass.
Normal startup imports match this freeze. Five targeted navigation cases and
one final offline suite are active on V17. Five full rendered acceptances and
96 campaign flights remain pending. V16 split failed 17/22 after 18 contacts
failed only the unchanged 0.30 s winch freshness requirement. Operator RTL,
actual connected disarm and all original grades/recordings are preserved.
24 negative geometry classifications and 80 weather exclusions are not passes.
Strong gusts and artificial delay remain unresolved and excluded.

## Prior checkpoints

'''+status.read_text(encoding='utf-8'),encoding='utf-8')
report=base/'evidence_report_20261007.md';text=report.read_text(encoding='utf-8')
start=text.index('The active provisional source is V16:');end=text.index('## Current-source targeted navigation')
text=text[:start]+f'''The active provisional source is V17: {prov['files']} controlled files, archive SHA256
`{prov['archive_sha256']}`. Five exact-source targeted navigation cases and the
final offline suite are active. Normal startup imports match the freeze.
The recorder now journals every actual winch status arrival before the next
5 Hz video snapshot; video cadence and every flight/grading threshold are unchanged.
The actual callback/contact-grader regression failed before the fix; 62 focused
checks pass, including stale/future arrivals, stowed/faulted winch, wrong phase,
off-target contact, wall contact and missing positions. Controller/perception and
the contact grader match V16 byte for byte. Source differences are archived in
`logs/reliability_reduced_scope_v17_source_20261008/change_from_v16.json`.
No earlier source evidence is counted as final qualification for V17.

'''+text[end:]
text=text.replace('## Current-source targeted navigation','## Prior-source V16 targeted navigation')
text=text.replace('| Strong gust/delayed control |','| V16 rendered split | 17/22; 18 target-floor contacts failed only winch freshness; safely interrupted, delivery confirmed and actual disarm | Preserved failure; not qualified |\n| Strong gust/delayed control |')
text=text.replace('Headless teardown sometimes logs', 'The V16 native contact recorder aborted during shutdown with a pybind11 GIL error after disarm. Contact coverage was valid; original stderr is preserved. This cleanup issue remains unresolved.\n\nHeadless teardown sometimes logs')
text=text[:text.index('## Work still required')]+'''## Work still required

Finish the five targeted navigation cases and final offline suite on V17, then
five full rendered acceptances (standard 20261003 and 1001; shipped, rotated and
split 20261003) and the 96-flight reduced campaign. Twenty-four negative geometry
classifications and 80 explicit weather exclusions are not passes. Preserve exact
source/configuration hashes, per-run detector rates, recordings, telemetry and
all failures. This report and machine index remain incomplete.
'''
report.write_text(text,encoding='utf-8')
print('V16 native failure closed without regrading; V17 provisional')
