"""Wait for owned recording closure, guard original source, then qualify the repair."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).parent
from fast_acceptance_source_manifest_20261007 import manifest
from launch_owned_job_20261006 import read_json
previous=root/'logs/reliability_banner_capture_qualification_continuity_owned_20261007'
evidence=root/'logs/reliability_pristine_banner_integration_20261007';evidence.mkdir(exist_ok=False)
review=root/'logs/reliability_clean_banner_review_patch_20261007'
assert json.loads((root/'logs/reliability_clean_banner_pixels_regressions_fixed_20261007/report.json').read_text())['exit_code']==0
assert json.loads((root/'logs/reliability_pristine_banner_new_regression_20261007/report.json').read_text())['exit_code']==0
status=read_json(previous/'status.json')
identity=status['command_process'];boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert identity['boot_id']==boot
def save(state,**extra):
    temporary=evidence/'report.json.writing';temporary.write_text(json.dumps(dict(state=state,wall_s=time.time(),**extra),indent=2)+'\n');temporary.replace(evidence/'report.json')
save('WAITING_FOR_PREVIOUS_RECORDING_AND_SOURCE_ARCHIVE',production_modified=False)
while True:
    status=read_json(previous/'status.json')
    assert status['command_process']==identity
    if status['state'] in ('COMPLETED','FAILED'):break
    assert status['state']=='RUNNING','Interrupted or errored qualification cannot authorize source changes'
    time.sleep(5)
qualified=root/'logs/reliability_banner_capture_qualification_continuity_20261007'
previous_report=json.loads((qualified/'report.json').read_text())
assert previous_report['source_unchanged'] and len(previous_report['rendered'])==1
trial=previous_report['rendered'][0]
assert trial['archive_exit_code']==0 and trial['runtime_visual_assets_captured'] and trial['summary']
assert trial['summary']['final_armed'] is False, 'Previous flight must actually disarm before integration'
assert previous_report['state'] in ('OBSERVATION_REPAIR_RENDERED_COURSES_PASSED','OBSERVATION_REPAIR_RENDERED_COURSES_FAILED')
frozen=json.loads((qualified/'source_manifest.json').read_text());assert manifest()==frozen
patch=json.loads((review/'report.json').read_text())
changes=[(patch['source_file'],patch['base_sha256'],patch['candidate_sha256'],'banner_node.py.candidate'),
         (patch['test_change']['source_file'],patch['test_change']['base_sha256'],patch['test_change']['candidate_sha256'],'test_banner_capture_contract.py.candidate')]
for name,base,candidate,artifact in changes:
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==base==frozen[name]
    assert hashlib.sha256((review/artifact).read_bytes()).hexdigest()==candidate
save('APPLYING_VERIFIED_PRISTINE_PIXEL_REPAIR',previous_rendered_pass=trial['summary'].get('acceptance_pass'),changes=[row[0] for row in changes])
for name,base,candidate,artifact in changes:
    temporary=(root/name).with_name(Path(name).name+'.pristine-writing')
    temporary.write_bytes((review/artifact).read_bytes());temporary.replace(root/name)
expected=dict(frozen)
for name,base,candidate,artifact in changes:expected[name]=candidate
assert manifest()==expected
save('RUNNING_FULL_SUITE_AND_FRESH_RENDERED_TRIAL',production_modified=True)
code=subprocess.call([sys.executable,str(here/'qualify_pristine_banner_20261007.py')],cwd=root)
save('CLOSED',exit_code=code,production_modified=True,overall_simulation_qualified=False)
raise SystemExit(code)
