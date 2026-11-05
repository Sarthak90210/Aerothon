"""Preserve the earlier audit and independently check the closed baseline."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
original = Path(__file__).with_name('review_coupled_snapshot_20261006.py')
code = original.read_text().replace('coupled_snapshot_independent_review_20261006.json',
                                   'closed_baseline_byte_review_20261007.json')
exec(compile(code, str(original), 'exec'), dict(__file__=str(original), __name__='__main__'))
out = Path(__file__).with_name('closed_baseline_byte_review_20261007.json')
report = json.loads(out.read_text())
report['closed_matrix'] = json.loads((root/'logs/reliability_navigation_baseline_matrix_assets_20261006/report.json').read_text())
report['closed_matrix_owned_status'] = json.loads((root/'logs/reliability_navigation_baseline_matrix_assets_owned_20261006/status.json').read_text())
out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:report['closed_matrix'][k] for k in
    ('requested_trials','executed_trials','classified_without_flight','source_unchanged','navigation_passes')},indent=2))
