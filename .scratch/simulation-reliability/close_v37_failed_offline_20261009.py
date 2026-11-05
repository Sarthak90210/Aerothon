"""Preserve a completed failed full suite without upgrading any failure."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
source=root/'logs/reliability_reduced_scope_v37_source_20261008'
manifest=json.loads((root/'.scratch/reduced_scope_v37_candidate_20261008/source_manifest.json').read_text())
current={name.replace('\\','/'):sha for name,sha in source_manifest(root).items()}
assert current==manifest,dict(changed=[n for n in manifest if current.get(n)!=manifest[n]],added=[n for n in current if n not in manifest])
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
p=json.loads((source/'provenance.json').read_text());assert hashlib.sha256((source/'frozen_source.zip').read_bytes()).hexdigest()==p['archive_sha256']
with zipfile.ZipFile(source/'frozen_source.zip') as z:
 assert all(hashlib.sha256(z.read(name)).hexdigest()==sha for name,sha in manifest.items())
log=root/'logs/reliability_reduced_v37_full_offline_20261008.log';text=log.read_text(encoding='utf-8')
assert '8 failed, 1687 passed, 8 skipped' in text and 'OFFLINE CHECKS FAILED' in text
assert text.count('  -> ok')==4
scope=json.loads((source/'offline_scope_exclusions.json').read_text());assert scope['collected_tests']==1703
target=json.loads((source/'targeted_closed_review.json').read_text());assert target['pass_navigation'] and len(target['results'])==5
failures=re.findall(r'^_+ (.+?) _+$',text,re.MULTILINE);assert len(failures)==8,failures
review=dict(accepted_source=False,qualification_complete=False,all_offline_checks_pass=False,complete_suite_executed=True,source_unchanged=True,source_files=len(manifest),archive_verified=True,archive_sha256=p['archive_sha256'],pytest_failed=8,pytest_passed=1687,pytest_skipped=8,pytest_elapsed_s=3158.98,failures=failures,reduced_scope=True,original_full_suite_qualified=False,scope=scope,syntax_configuration_and_frontend_passed=True,targeted_navigation_passed=True,targeted_cases=5,rendered_acceptance_count=0,campaign_executed_count=0,files={f.name:dict(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size) for f in [log,source/'offline_scope_exclusions.json',root/'logs/reliability_v37_qualification_pipeline_20261008.log']})
with (source/'failed_full_offline_closed_review.json').open('x') as f:json.dump(review,f,indent=2)
base=root/'.scratch/simulation-reliability'
note='''## V37 completed verification result

All five exact-source normal-timing navigation cases passed all 13 checks,
with actual disarm and zero contacts/fence breaches. The complete reduced
offline suite then FAILED: 8 failed, 1687 passed, 8 skipped, 3158.98 seconds.
Python/shell syntax, XML/YAML parsing and the frontend build passed. One
failure is a missing UI state for CameraBannerReturnAlignment. Seven
search-hold fixtures expect completion while still inside the observed
1.50 m exclusion margin; their interaction with the stricter escape policy
requires correction and validation. No threshold or assertion has been
waived. The source, completed failed log, exclusion ledger and exact
failure names are preserved in failed_full_offline_closed_review.json.
No native acceptance or campaign ran, and V37 is not an accepted source.

'''
for name in ['status.md','evidence_report_20261007.md']:
 f=base/name;s=f.read_text(encoding='utf-8')
 if '## V37 completed verification result' not in s:f.write_text(note+s,encoding='utf-8')
f=base/'evidence_index_20261007.json';index=json.loads(f.read_text(encoding='utf-8'))
index['active_runs']=[];index['active_trial']=None;index['qualification_complete']=False;index['accepted_source']=None
index['verification']['v37_failed_offline_review']='logs/reliability_reduced_scope_v37_source_20261008/failed_full_offline_closed_review.json'
index['current_continuation']['remaining']='Fix UI state and seven search-hold fixtures, focused checks, final source qualification'
f.write_text(json.dumps(index,indent=2),encoding='utf-8')
print(json.dumps(dict(failed=8,passed=1687,skipped=8,targeted_navigation_passes=5,accepted=False)))
