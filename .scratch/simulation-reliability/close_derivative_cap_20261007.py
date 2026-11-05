"""Preserve the rejected derivative diagnostic and its exact baseline."""
import ast, hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_derivative_cap_1_6_coupled_20261007'
baseline=root/'.scratch/command_deadline_candidate_20261007/src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
current=root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
method_tree=lambda p: [ast.dump(n) for c in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef)]
assert method_tree(baseline)==method_tree(current)
provenance=json.loads((out/'candidate_provenance.json').read_text())
assert hashlib.sha256((out/'candidate_compensation.py').read_bytes()).hexdigest()==provenance['candidate_sha256']
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==provenance['baseline_sha256']
for source,name in ((baseline,'baseline_controller.py'),(Path(__file__).with_name('check_command_deadline_coupled_20261007.py'),'baseline_runner.py')):
    with (out/name).open('xb') as stream: stream.write(source.read_bytes())
summary=json.loads((out/'summary.json').read_text())
assert not summary['all_pass'] and all(not c['passed'] for c in summary['cases'])
files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
review=dict(scope='Frozen buffered/deadline physical fixture, derivative cap only',
    baseline_class_methods_match_current=True, baseline_startup_differs=True,
    physical_delay_s=.4, response_s=.6, derivative_cap_mps2=1.6,
    production_adopted=False, cases=summary['cases'], files_sha256=files)
with (out/'closed_rejected_review_20261007.json').open('x') as stream: json.dump(review,stream,indent=2)
print('Both cases rejected; exact candidate, baseline, runner and results archived')
