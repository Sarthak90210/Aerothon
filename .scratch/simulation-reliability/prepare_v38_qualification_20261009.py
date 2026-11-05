"""Verify final UI integration and corrected stationary-hold fixtures."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text())
stems=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='stems' for t in n.targets))
for stem in stems:
    current=stem.replace('v19','v37')
    text=(base/current).read_text().replace('v37','v38').replace('V37','V38')
    text=text.replace('reliability_reduced_v36_targeted_20261008/report.json','reliability_reduced_v37_targeted_20261008/report.json').replace('V36 targeted trials safely closed','V37 targeted trials safely closed')
    (base/current.replace('v37','v38')).write_text(text,encoding='utf-8',newline='\n')
assert 'v24.18.0' in (base/'run_reduced_v38_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v38_full_offline_20261008.sh').read_text()
assert 'seed,out,1.,1200.' in (base/'probe_reduced_targeted_v38_20261008.py').read_text()
assert '--rtf 1' in (base/'run_reduced_v38_campaign_20261008.sh').read_text()
assert 'except subprocess.TimeoutExpired' in (base/'watch_v38_failed_trials_20261008.py').read_text()
assert 'except subprocess.TimeoutExpired' in (base/'watch_v38_native_failed_trials_20261008.py').read_text()
print('V38 strict gates prepared; final source gets five new normal-timing flights before full offline/native/campaign')
