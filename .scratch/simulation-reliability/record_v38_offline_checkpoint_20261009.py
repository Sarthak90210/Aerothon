"""Record sealed offline pass and live native trial without qualifying it."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / '.scratch/simulation-reliability'
review_path = 'logs/reliability_reduced_scope_v38_source_20261008/full_offline_closed_review.json'
review = json.loads((root / review_path).read_text())
assert review['all_offline_checks_pass'] and review['source_unchanged']
assert review['pytest_passed'] == 1697 and review['pytest_skipped'] == 8
trial = 'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
assert (root / trial / 'vehicle_contact_ready.json').exists()
old = ('The complete reduced offline suite is running. Five native 22/22\n'
       'acceptances and 96 eligible campaign flights remain pending. No source is\n'
       'accepted yet and no original 200-case qualification is claimed.')
new = ('The complete reduced offline suite PASSED: 1697 tests passed, eight\n'
       'skipped (five deferred strong-gust tests, three empty photograph-corpus\n'
       'tests). Syntax, configuration parsing and the frontend build also pass.\n'
       'Source closure verifies all 949 controlled files unchanged. The first\n'
       'rendered split-course acceptance is active; all five final native 22/22\n'
       'acceptances and 96 eligible campaign flights remain unqualified. No\n'
       'source is accepted yet and no original 200-case qualification is claimed.')
for name in ['status.md', 'evidence_report_20261007.md']:
    path = base / name
    text = path.read_text(encoding='utf-8')
    if old in text:
        path.write_text(text.replace(old, new, 1), encoding='utf-8')
path = base / 'evidence_index_20261007.json'
index = json.loads(path.read_text(encoding='utf-8'))
index['active_runs'] = [trial]
index['active_trial'] = trial
index['verification']['v38_full_offline_closed_review'] = review_path
index['current_continuation']['remaining'] = 'Five final-source rendered acceptances, 96 eligible campaign flights and consolidated final closure'
path.write_text(json.dumps(index, indent=2), encoding='utf-8')
print('Sealed offline PASS recorded; rendered qualification remains pending.')
