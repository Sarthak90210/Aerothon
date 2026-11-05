"""Wait for disarm/archive, verify source, install reviewed files and qualify."""
import hashlib
import json
import subprocess
import time
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
here=Path(__file__).parent
sys.path.insert(0,str(here))
from fast_acceptance_source_manifest_20261007 import manifest
out=root/'logs/reliability_early_red_clipped_bearing_integration_20261007';out.mkdir(exist_ok=False)
report=dict(state='WAITING_FOR_PRISTINE_RECORDING_AND_SOURCE_ARCHIVE',production_modified=False)
def save():
    tmp=out/'report.json.writing';tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(out/'report.json')
save()
prior=root/'logs/reliability_pristine_banner_qualification_20261007'
while True:
    value=json.loads((prior/'report.json').read_text())
    if value['state'] in ('OBSERVATION_REPAIR_RENDERED_COURSES_PASSED','OBSERVATION_REPAIR_RENDERED_COURSES_FAILED'):
        break
    if value['state'] not in ('RUNNING_COMPLETE_OFFLINE_SUITE','RUNNING_FRESH_RENDERED_COURSES'):
        raise RuntimeError(value['state'])
    time.sleep(5)
assert value['source_unchanged'] and value['full_suite_exit_code']==0
assert len(value['rendered'])==1
previous=value['rendered'][0]
assert previous['archive_exit_code']==0 and previous['runtime_visual_assets_captured']
summary=previous['summary'];assert summary['final_armed'] is False
frozen=json.loads((prior/'source_manifest.json').read_text());assert manifest()==frozen
patch=json.loads((root/'logs/reliability_rendered_perception_review_patch_20261007/report.json').read_text())
assert '130 passed' in (root/'logs/reliability_search_braking_regressions_20261007.log').read_text()
assert '94 passed' in (root/'logs/reliability_provisional_red_regressions_owned_20261007/output.log').read_text()
assert '139 passed' in (root/'logs/reliability_clipped_banner_bearing_regressions_owned_20261007/output.log').read_text()
qr=json.loads((root/'logs/reliability_provisional_red_qr_callbacks_20261007.json').read_text())
assert qr['rejected_all'] and qr['cases']==432
for change in patch['changes']:
    target=root/change['path'];prepared=root/change['candidate']
    actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    assert actual==change['base_sha256'],change['path']
    assert hashlib.sha256(prepared.read_bytes()).hexdigest()==change['candidate_sha256']
report.update(state='INSTALLING_REVIEWED_REPAIRS',previous_rendered_pass=summary.get('acceptance_pass'),
              previous_archive_verified=True,files=len(patch['changes']));save()
for change in patch['changes']:
    target=root/change['path'];target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes((root/change['candidate']).read_bytes())
report.update(state='RUNNING_FULL_SUITE_AND_FRESH_RENDERED_TRIALS',production_modified=True);save()
with (out/'qualification.log').open('xb') as stream:
    code=subprocess.run(['/usr/bin/python3',str(here/'qualify_early_red_clipped_bearing_20261007.py')],
        cwd=root,stdout=stream,stderr=subprocess.STDOUT).returncode
report.update(state='QUALIFICATION_PASSED' if code==0 else 'QUALIFICATION_FAILED',exit_code=code);save()
raise SystemExit(code)
