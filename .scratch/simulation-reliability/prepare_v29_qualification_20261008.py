"""Prepare measured-motion gate recovery after the closed V28 failures."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
 current=old.replace('v19','v28');text=(base/current).read_text(encoding='utf-8').replace('v28','v29').replace('V28','V29')
 if old in ['run_v19_qualification_gates_20261008.py','probe_reduced_targeted_v19_20261008.py']:
  text=text.replace('reliability_reduced_v27_targeted_20261008/report.json','reliability_reduced_v28_targeted_20261008/report.json')
  text=text.replace('V27 targeted trials safely closed','V28 targeted trials safely closed')
 (base/current.replace('v28','v29')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v29_full_offline_20261008.sh').read_text(encoding='utf-8')
print('V29 prepared with strict sequential qualification gates')
