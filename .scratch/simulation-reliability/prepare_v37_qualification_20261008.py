"""Exact-clock gate guard and normal real-time object flight configuration."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text())
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for stem in stems:
    current=stem.replace('v19','v36')
    text=(base/current).read_text().replace('v36','v37').replace('V36','V37')
    text=text.replace('reliability_reduced_v35_targeted_20261008/report.json','reliability_reduced_v36_targeted_20261008/report.json').replace('V35 targeted trials safely closed','V36 targeted trials safely closed')
    if current=='probe_reduced_targeted_v36_20261008.py':text=text.replace('seed,out,2.,1200.','seed,out,1.,1200.').replace('RTF2','RTF1')
    if current=='close_reduced_v36_targeted_20261008.py':text=text.replace("cfg['rtf']==2", "cfg['rtf']==1")
    if current=='close_reduced_v36_qualification_20261008.py':text=text.replace("cfg['rtf'] == 2", "cfg['rtf'] == 1")
    if current=='run_reduced_v36_campaign_20261008.sh':text=text.replace('--rtf 2','--rtf 1')
    (base/current.replace('v36','v37')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v37_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v37_full_offline_20261008.sh').read_text()
print('V37 strict gates prepared; object flights use real-time simulation, normal rates/response and zero extra queue')
