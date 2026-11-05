"""Gate the revised sweep and timestamp pause on one newly frozen source."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v21')
    text=(base/current).read_text(encoding='utf-8').replace('v21','v22').replace('V21','V22')
    if old=='run_v19_qualification_gates_20261008.py':
        text=text.replace("root/'logs/reliability_reduced_v20_targeted_20261008/report.json'",
                          "root/'logs/reliability_reduced_scope_v21_source_20261008/interrupted_batch_closed_review.json'")
        text=text.replace('V20 focused trials closed','V21 processes absent and interrupted batch retained')
    (base/current.replace('v21','v22')).write_text(text,encoding='utf-8',newline='\n')
print('V22 gates prepared; five targeted navigation checks before final offline/native/campaign')
