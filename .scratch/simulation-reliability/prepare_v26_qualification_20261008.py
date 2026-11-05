"""Prepare framing classification; keep the prior batch isolated to disarm."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v25')
    text=(base/current).read_text(encoding='utf-8').replace('v25','v26').replace('V25','V26')
    if old=='run_v19_qualification_gates_20261008.py':
        text=text.replace('reliability_reduced_v24_targeted_20261008','reliability_reduced_v25_targeted_20261008')
        text=text.replace('V24 focused trials closed','V25 focused trials closed')
    (base/current.replace('v25','v26')).write_text(text,encoding='utf-8',newline='\n')
print('V26 prepared; prior V25 must actually disarm before reusing domains')
