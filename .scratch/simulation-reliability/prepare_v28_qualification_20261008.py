"""Clone the closed candidate's gates; retain actual installed runtime paths."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text())
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
 current=old.replace('v19','v27')
 text=(base/current).read_text(encoding='utf-8').replace('v27','v28').replace('V27','V28')
 if old=='run_v19_qualification_gates_20261008.py':
  text=text.replace('reliability_reduced_v26_targeted_20261008/my_world_field_s3/navigation_grade.json','reliability_reduced_v27_targeted_20261008/report.json')
  text=text.replace('V26 domain 41 trial closed; V28 can use it while domain 40 waits for the prior batch to close','V27 targeted trials safely closed; V28 reuses domains 40 and 41')
 if old=='probe_reduced_targeted_v19_20261008.py':
  text=text.replace('reliability_reduced_v26_targeted_20261008/report.json','reliability_reduced_v27_targeted_20261008/report.json')
 (base/current.replace('v27','v28')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v28_full_offline_20261008.sh').read_text()
print('V28 gates prepared; both prior trials closed; actual Node path retained')
