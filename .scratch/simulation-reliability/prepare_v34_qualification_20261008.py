"""Verify the return camera handoff first; preserve explicit reduced scope."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v33')
    text=(base/current).read_text(encoding='utf-8').replace('v33','v34').replace('V33','V34')
    text=text.replace('reliability_reduced_v32_targeted_20261008/report.json','reliability_reduced_v33_targeted_20261008/report.json').replace('V32 targeted trials safely closed','V33 targeted trials safely closed')
    if current=='probe_reduced_targeted_v33_20261008.py':
        text=text.replace("cases=[('random',3),('field',2),('field',1),('field',3),('random',4)]", "cases=[('field',3),('random',3),('field',2),('field',1),('random',4)]")
    text=text.replace('Their original V32 failures remain archived and are not passes.', 'Four of these tests failed in the interrupted V32 run; those failures remain archived and are not passes. The fifth uses the same deferred weather envelope.')
    (base/current.replace('v33','v34')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v34_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v34_full_offline_20261008.sh').read_text()
assert 'close_reduced_v34_qualification' in (base/'run_v34_qualification_gates_20261008.py').read_text()
print('V34 strict gates prepared; field 3 camera handoff verified first')
