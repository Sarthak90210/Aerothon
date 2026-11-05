"""Prepare gate braking candidate, prioritising the reproduced mild failure."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text())
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for stem in stems:
    current=stem.replace('v19','v34')
    text=(base/current).read_text().replace('v34','v35').replace('V34','V35')
    text=text.replace('reliability_reduced_v33_targeted_20261008/report.json','reliability_reduced_v34_targeted_20261008/report.json').replace('V33 targeted trials safely closed','V34 targeted trials safely closed')
    if current=='probe_reduced_targeted_v34_20261008.py':
        text=text.replace("cases=[('field',3),('random',3),('field',2),('field',1),('random',4)]", "cases=[('random',3),('field',3),('field',2),('field',1),('random',4)]")
    (base/current.replace('v34','v35')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v35_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v35_full_offline_20261008.sh').read_text()
print('V35 strict qualification gates prepared; reproduced mild seed 3 runs first')
