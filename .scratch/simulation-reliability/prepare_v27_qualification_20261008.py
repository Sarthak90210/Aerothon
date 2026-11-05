"""Prepare strict return climb; stop queueing candidates after a failed case."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for old in stems:
    current=old.replace('v19','v26')
    text=(base/current).read_text(encoding='utf-8').replace('v26','v27').replace('V26','V27')
    if old=='run_v19_qualification_gates_20261008.py':
        text=text.replace('reliability_reduced_v25_targeted_20261008','reliability_reduced_v26_targeted_20261008')
        text=text.replace('V25 focused trials closed','V26 focused trials closed')
    if old=='probe_reduced_targeted_v19_20261008.py':
        text=text.replace('from pathlib import Path','from pathlib import Path\nfrom threading import Event')
        text=text.replace("cases=[('random',3)","stop_queue=Event()\ncases=[('random',3)")
        text=text.replace(' for weather,seed in work:\n',' for weather,seed in work:\n  if stop_queue.is_set():break\n')
        text=text.replace('  result.append(r);print(json.dumps(r),flush=True)','  result.append(r);print(json.dumps(r),flush=True)\n  if not r[\'navigation_pass\']:stop_queue.set()')
        text=text.replace("pass_navigation=unchanged and all(r['navigation_pass'] for r in results)","pass_navigation=unchanged and len(results)==len(cases) and all(r['navigation_pass'] for r in results),planned_cases=len(cases),executed_cases=len(results),cancelled_unflown_cases=len(cases)-len(results)")
    (base/current.replace('v26','v27')).write_text(text,encoding='utf-8',newline='\n')
print('V27 prepared; no armed trial will be interrupted; failed candidates stop queueing unflown cases')
