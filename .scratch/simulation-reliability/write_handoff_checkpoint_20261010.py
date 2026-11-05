"""Seal a user-requested stop checkpoint without running qualification."""
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / '.scratch/simulation-reliability'
def read(p):
    return json.loads(p.read_text(encoding='utf-8'))
def files(p):
    return {x.name: {'bytes': x.stat().st_size, 'sha256': hashlib.sha256(x.read_bytes()).hexdigest()}
            for x in p.iterdir() if x.is_file()}

manifest = read(root / '.scratch/reduced_scope_v39_candidate_20261008/source_manifest.json')
assert all(hashlib.sha256((root/n.replace('\\','/')).read_bytes()).hexdigest() == sha for n,sha in manifest.items())
source = root / 'logs/reliability_reduced_scope_v39_source_20261008'
archive_sha = hashlib.sha256((source/'frozen_source.zip').read_bytes()).hexdigest()
targeted = read(source/'targeted_closed_review.json')
assert targeted['pass_navigation'] and len(targeted['results']) == 5
native = root/'logs/reliability_reduced_v39_focused_split_s20261003_20261009'
focused = read(native/'focused_summary.json')
result = read(native/'recorded_result.json')
assert result['disarm_evidence']['connected'] and not result['disarm_evidence']['armed']
grade = read(native/'grade.json')
c = grade['aircraft_contact_evidence']
unexpected = c['unexpected_contacts']
grouped = {}
for event in unexpected:
    pair = event['vehicle'] + ' -> ' + event['other']
    item = grouped.setdefault(pair, dict(count=0, first_stamp=event['stamp'], last_stamp=event['stamp'], during_recorded_armed_interval=0))
    item['count'] += 1
    item['last_stamp'] = event['stamp']
    if c['first_armed_stamp'] <= event['stamp'] <= c['last_armed_stamp']:
        item['during_recorded_armed_interval'] += 1
terms = ['qualification_gates', 'probe_reduced_targeted', 'watch_v39', 'fly_headless', 'corridor_trial',
         'run_recorded_acceptance', 'gz sim', 'arducopter', 'ros2 launch']
process_code = "import subprocess; rows=subprocess.check_output(['ps','-eo','pid,ppid,etime,args'],text=True).splitlines(); terms=" + repr(terms) + "; print('\\n'.join(r for r in rows if any(t in r for t in terms) and 'python3 -c' not in r and 'wsl -d' not in r))"
ps = subprocess.run(['wsl','-d','Ubuntu','-u','sarthak','--','python3','-c',process_code], capture_output=True, text=True, timeout=20)
assert ps.returncode == 0 and not ps.stdout.strip(), (ps.returncode, ps.stdout, ps.stderr)
timestamp = datetime.now().astimezone().isoformat()
targeted_compact = [{k: r[k] for k in ('weather','seed','path','flight_time_s','corridor_clearance_m','red_clearance_m','connected_disarm','configuration')}
                    for r in targeted['results']]
checkpoint = dict(timestamp=timestamp, user_instruction='Stop work and write an executive handoff',
    status='stopped_by_user', accepted_source=None, qualification_complete=False, original_200_case_qualified=False,
    source_files=len(manifest), source_unchanged=True, source_archive_sha256=archive_sha,
    pipeline_exit_code=1, pipeline_stop_reason='Focused native independent contact-free assertion failed',
    process_verification=dict(returncode=ps.returncode, matching_processes=[], terms=terms, stderr=ps.stderr),
    targeted_navigation=dict(executed=5, passed=5, cancelled=0, cases=targeted_compact,
        rendered_perception_qualified=False, motor_delivery_qualified=False),
    focused_native=dict(geometric_checks_passed=7, independent_clearance_m=focused['measured_corridor_clearance_m'],
        recorded_result=result, focused_source_closed_review_exists=(native/'focused_source_closed_review.json').exists(),
        full_mission_qualified=False, contact_evidence={k:v for k,v in c.items() if k!='unexpected_contacts'},
        unexpected_contact_count=len(unexpected), unexpected_contact_groups=grouped,
        detector_rates=grade['detector_rates'], configuration=read(native/'configuration.json'), artifact_hashes=files(native)),
    not_started=['V39 full reduced offline suite','V39 five full rendered acceptances','V39 96-flight reduced campaign','final accepted evidence closure'],
    deferred_unresolved=['Strong-gust contacts','Artificially delayed-control contacts/return failures'])
receipt=base/'handoff_stop_checkpoint_20261010.json'
receipt.write_text(json.dumps(checkpoint,indent=2)+'\n',encoding='utf-8')
index_path=base/'evidence_index_20261007.json'
index=read(index_path)
index.update(accepted_source=None,qualification_complete=False,campaign_200_qualified=False,active_runs=[],active_trial=None,
    current_continuation=dict(source='V39 provisional',source_files=len(manifest),archive_sha256=archive_sha,
        headless_rtf=1.,status='stopped_by_user',stop_checkpoint=str(receipt.relative_to(root)).replace('\\','/'),
        remaining='Resolve focused native contact failure; full reduced offline suite; five full native acceptances; 96-flight campaign; final evidence closure'),
    next_diagnostic='Resume only after user instruction. Inspect focused V39 unloaded payload/skid contacts and post-disarm ground contact classification; keep all failures.')
index_path.write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
preamble=f'''# Stopped by user, executive handoff checkpoint {timestamp}

No qualification or mission process is active. The five V39 targeted navigation
cases passed all 13 navigation checks and actually disarmed. The short native
moving-handover return completed all seven geometric/evidence checks at
0.758286655 m clearance and connected disarm. Its separate contact-free closure
FAILED: 6805 unexpected contact records are preserved. No full V39 offline suite,
five full native acceptances, or 96-flight campaign started. V39 remains unaccepted.

Source verification at handoff confirms all 951 controlled files unchanged and
archive SHA256 {archive_sha}.
Strong gusts and artificially delayed control remain unresolved and excluded.
Do not resume automatically. See EXECUTIVE_HANDOFF_20261010.md and
handoff_stop_checkpoint_20261010.json for current state. Older headings below
are chronological checkpoints and may describe work that has since stopped.

'''
for name in ('status.md','evidence_report_20261007.md'):
    p=base/name
    old=p.read_text(encoding='utf-8')
    if not old.startswith('# Stopped by user, executive handoff checkpoint'):
        p.write_text(preamble+old,encoding='utf-8')
print(json.dumps(dict(checkpoint=str(receipt),timestamp=timestamp,source_files=len(manifest),contact_groups=grouped,
    targeted=targeted_compact,processes_active=False),indent=2))
