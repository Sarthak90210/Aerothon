"""Prepare one-variable landing capture-gap correction after closed V29."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
 current=old.replace('v19','v29')
 text=(base/current).read_text(encoding='utf-8').replace('v29','v30').replace('V29','V30')
 text=text.replace('reliability_reduced_v28_targeted_20261008/report.json','reliability_reduced_v29_targeted_20261008/report.json').replace('V28 targeted trials safely closed','V29 targeted trials safely closed')
 (base/current.replace('v29','v30')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v30_full_offline_20261008.sh').read_text(encoding='utf-8')
assert 'close_reduced_v30_qualification' in (base/'run_v30_qualification_gates_20261008.py').read_text(encoding='utf-8')
print('V30 gates prepared; all five source-matched targeted cases required')
