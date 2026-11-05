import hashlib,json,sys,re
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest
snapshot=root/'.scratch/reduced_scope_v41_candidate_20261010'
manifest=json.loads((snapshot/'source_manifest.json').read_text());source_manifest.cache_clear()
assert manifest==source_manifest(root),'Controlled source set changed during full suite'
assert all(hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==sha for name,sha in manifest.items())
log=root/'logs/reliability_reduced_v41_full_offline_20261010.log'
text=log.read_text();assert 'ALL IN-SCOPE OFFLINE CHECKS PASSED' in text,text[-800:]
assert 'SKIPPED (node_modules absent' not in text, 'Frontend was not exercised'
pytest_summary=re.findall(r'(\d+) passed(?:, (\d+) skipped)?',text)
assert pytest_summary, 'Missing pytest completion summary'
out=root/'logs/reliability_reduced_scope_v41_source_20261010/full_offline_closed_review.json'
review=dict(all_offline_checks_pass=True,source_files=len(manifest),source_unchanged=True,
            pytest_passed=int(pytest_summary[-1][0]),pytest_skipped=int(pytest_summary[-1][1] or 0),frontend_exercised=True,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),accepted_source=False)
from qualification_offline_scope import DEFERRED_FLIGHTS
scope_path=out.parent/'offline_scope_exclusions.json'
scope=json.loads(scope_path.read_text())
assert scope['reduced_scope'] and not scope['original_full_suite_qualified']
assert scope['excluded_test_count']==5
assert {r['nodeid'] for r in scope['excluded_tests']}==DEFERRED_FLIGHTS
assert scope['fixture_source_sha256']==manifest['sim/test_corridor_stress.py']
assert scope['collected_tests']==review['pytest_passed']+review['pytest_skipped']
assert review['pytest_skipped']==8, 'Expected three empty photograph checks and five explicitly deferred gust flights'
review.update(reduced_scope=True,original_full_suite_qualified=False,excluded_offline_tests=scope['excluded_tests'],scope_ledger_sha256=hashlib.sha256(scope_path.read_bytes()).hexdigest(),deferred_test_count=5,empty_photograph_test_count=3)
with out.open('x') as f:json.dump(review,f,indent=2)
