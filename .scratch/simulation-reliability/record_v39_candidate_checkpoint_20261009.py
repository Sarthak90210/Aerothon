"""Record the new unaccepted candidate and preserve exact failed native evidence."""
import hashlib
import json
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
old=root/'logs/reliability_reduced_scope_v38_source_20261008'
run=root/'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
manifest=json.loads((root/'.scratch/reduced_scope_v38_candidate_20261008/source_manifest.json').read_text())
provenance=json.loads((old/'provenance.json').read_text())
assert hashlib.sha256((old/'frozen_source.zip').read_bytes()).hexdigest()==provenance['archive_sha256']
recorded=json.loads((run/'source_manifest.json').read_text())
with zipfile.ZipFile(old/'frozen_source.zip') as archive:
    assert all(recorded[name]==sha and hashlib.sha256(archive.read(name)).hexdigest()==sha for name,sha in manifest.items())
summary=json.loads((run/'summary.json').read_text());grade=json.loads((run/'grade.json').read_text())
assert summary['acceptance_pass'] is False and summary['final_armed'] is False
closed=dict(accepted_source=False,qualification_pass=False,source_archive_verified=True,
    archive_sha256=provenance['archive_sha256'],source_files=len(manifest),
    summary=summary,grade=grade,
    independent_minimum_m=json.loads((run/'return_clearance_diagnosis.json').read_text())['minimum_clearance_m'],
    files={str(path.relative_to(run)):dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
           for path in run.rglob('*') if path.is_file()},
    retained_status='17/22 FAILED, safe RTL and actual disarm; never upgraded by separate overhead-camera demonstration')
path=old/'native_split_failure_closed_review.json'
if not path.exists():path.write_text(json.dumps(closed,indent=2))
current=root/'logs/reliability_reduced_scope_v39_source_20261008'
new=json.loads((current/'provenance.json').read_text())
focus=(root/'logs/reliability_v39_continuous_certificate_focused_20261009.log').read_text(encoding='utf-8')
assert '40 passed' in focus
note=('## V39 continuous-clearance candidate; qualification active\n\n'
      f"Source freeze: {new['files']} controlled files; archive SHA256\n{new['archive_sha256']}. Source remains unaccepted.\n\n"
      'The actual native safe-origin scan reproduces an early planner stop\n'
      'at 0.720 m. Fixed spatial sampling reserves were applied even to\n'
      'stationary origins and short forecast intervals, then the compiled\n'
      'shortcut stage repeated the same rejection. V39 uses a continuous\n'
      '1-Lipschitz distance lower bound and bounded subdivision, with the\n'
      'unchanged 0.70 m floor and unknown-space checks. The compiled fast\n'
      'path and 0.025 m grid reserve remain; a failed shortcut batch can\n'
      'use that same full-clearance certificate. Filtering, thin returns,\n'
      'normal timing and actuator behaviour remain unchanged.\n\n'
      'Six new controls failed before the fix, while four safety negatives\n'
      'passed. Forty focused checks now pass. The actual normal 0.6 s\n'
      'airframe hold, with zero added queue, changes from 0.615 m failure\n'
      'to 0.700267746 m clearance. These are focused sensor/physical seams,\n'
      'not a completed native mission. All required V39 gates remain.\n\n'
      'The original V38 native 17/22 failure is sealed with all artifact\n'
      'hashes, independent truth, exact archived source, recorded RTL and\n'
      'actual disarm. The separate overhead-camera demonstration remains\n'
      'separate configuration evidence. Strong gusts and artificially\n'
      'delayed control remain unresolved and excluded.\n\n')
for name in ['status.md','evidence_report_20261007.md']:
    path=base/name;text=path.read_text(encoding='utf-8')
    if not text.startswith('## V39 continuous-clearance candidate;'):
        path.write_text(note+text,encoding='utf-8')
path=base/'evidence_index_20261007.json';index=json.loads(path.read_text(encoding='utf-8'))
index['verification']['v38_native_split_failure_closed_review']='logs/reliability_reduced_scope_v38_source_20261008/native_split_failure_closed_review.json'
index['verification']['v39_candidate_source']='logs/reliability_reduced_scope_v39_source_20261008/provenance.json'
index['verification']['v39_focused_checks']='logs/reliability_v39_continuous_certificate_focused_20261009.log'
index['current_continuation']['status']='active'
index['current_continuation']['remaining']='V39 startup verification, five targeted flights, focused native return, final offline suite, five full native acceptances and 96 campaign flights'
path.write_text(json.dumps(index,indent=2),encoding='utf-8')
print(json.dumps(dict(candidate_source_files=new['files'],focused_passes=40,v38_failed_native_sealed=True,accepted_source=False)))
