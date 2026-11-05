"""Clone the existing qualification gates for the guarded search candidate."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text())
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v20')
    text=(base/current).read_text().replace('v20','v21').replace('V20','V21')
    if old=='run_v19_qualification_gates_20261008.py':
        text=text.replace('reliability_reduced_v19_targeted_20261008','reliability_reduced_v20_targeted_20261008')
        text=text.replace('V19 focused trials closed','V20 focused trials closed')
    (base/current.replace('v20','v21')).write_text(text,encoding='utf-8',newline='\n')
print('V21 gates prepared; retained mild seed 3 and field seed 2 first')
