"""Prepare one-source speed-lease qualification after the prior flights close."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v22')
    text=(base/current).read_text(encoding='utf-8').replace('v22','v23').replace('V22','V23')
    if old=='run_v19_qualification_gates_20261008.py':
        text=text.replace("root/'logs/reliability_reduced_scope_v21_source_20261008/interrupted_batch_closed_review.json'",
                          "root/'logs/reliability_reduced_v22_targeted_20261008/report.json'")
        text=text.replace('V21 processes absent and interrupted batch retained','V22 focused trials closed')
    (base/current.replace('v22','v23')).write_text(text,encoding='utf-8',newline='\n')
print('V23 prepared; prior V22 flight must close before new domains are used')
