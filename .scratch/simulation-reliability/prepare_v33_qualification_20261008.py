"""Freeze explicit deferred offline scope; controller bytes remain unchanged."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v32')
    text=(base/current).read_text(encoding='utf-8').replace('v32','v33').replace('V32','V33')
    text=text.replace('reliability_reduced_v31_targeted_20261008/report.json','reliability_reduced_v32_targeted_20261008/report.json').replace('V31 targeted trials safely closed','V32 targeted trials safely closed')
    text=text.replace('final offline suite','final reduced-scope offline suite').replace('full offline suite','complete reduced-scope offline suite').replace('Final offline suite PASS','Reduced-scope offline suite PASS')
    if current=='run_reduced_v32_full_offline_20261008.sh':
        text=text.replace('bash scripts/run_tests.sh 2>&1', 'export AEROTHON_OFFLINE_SCOPE_EVIDENCE="$PWD/logs/reliability_reduced_scope_v33_source_20261008/offline_scope_exclusions.json"\nbash scripts/run_tests.sh --reduced-scope 2>&1')
    if current=='close_reduced_v32_offline_20261008.py':
        text=text.replace("assert 'ALL OFFLINE CHECKS PASSED' in text or 'ALL CHECKS PASSED' in text", "assert 'ALL IN-SCOPE OFFLINE CHECKS PASSED' in text")
        text=text.replace("with out.open('x') as f:json.dump(review,f,indent=2)", """from qualification_offline_scope import DEFERRED_FLIGHTS
scope_path=out.parent/'offline_scope_exclusions.json'
scope=json.loads(scope_path.read_text())
assert scope['reduced_scope'] and not scope['original_full_suite_qualified']
assert scope['excluded_test_count']==5
assert {r['nodeid'] for r in scope['excluded_tests']}==DEFERRED_FLIGHTS
assert scope['fixture_source_sha256']==manifest['sim/test_corridor_stress.py']
assert scope['collected_tests']==review['pytest_passed']+review['pytest_skipped']
assert review['pytest_skipped']==8, 'Expected three empty photograph checks and five explicitly deferred gust flights'
review.update(reduced_scope=True,original_full_suite_qualified=False,excluded_offline_tests=scope['excluded_tests'],scope_ledger_sha256=hashlib.sha256(scope_path.read_bytes()).hexdigest(),deferred_test_count=5,empty_photograph_test_count=3)
with out.open('x') as f:json.dump(review,f,indent=2)""")
    if current=='close_reduced_v32_qualification_20261008.py':
        text=text.replace("assert offline['all_offline_checks_pass'] and offline['source_unchanged']", """assert offline['all_offline_checks_pass'] and offline['source_unchanged']
assert offline['reduced_scope'] and not offline['original_full_suite_qualified']
scope_path=source/'offline_scope_exclusions.json'
assert hashlib.sha256(scope_path.read_bytes()).hexdigest()==offline['scope_ledger_sha256']
assert offline['deferred_test_count']==5 and offline['empty_photograph_test_count']==3""")
        text=text.replace("original_200_case_qualified=False,offline=offline", "original_200_case_qualified=False,original_full_offline_suite_qualified=False,offline=offline,offline_scope_exclusions=json.loads(scope_path.read_text())")
        text=text.replace("'The three skips are the empty real-photograph", "'Five offline flight tests using mean wind 8 m/s and gust 4 m/s are explicitly skipped under the user-deferred scope. Their original V32 failures remain archived and are not passes. The other three skips are the empty real-photograph")
        text=text.replace("'* Three empty real-photograph corpus checks remain skipped;", "'* Five strong-gust offline flight tests remain explicitly excluded and unresolved; their original failures are preserved.',\n          '* Three empty real-photograph corpus checks remain skipped;")
    (base/current.replace('v32','v33')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v33_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v33_full_offline_20261008.sh').read_text()
print('V33 exact-source gates prepared, with explicit deferred offline scope')
