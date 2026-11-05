"""Freeze continuous certificates; native replay gate precedes the full suite."""
import ast
import hashlib
import json
import math
from pathlib import Path

root=Path(__file__).resolve().parents[2];base=root/'.scratch/simulation-reliability'
tree=ast.parse((base/'prepare_v20_qualification_20261008.py').read_text(encoding='utf-8'))
stems=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
    and any(isinstance(target,ast.Name) and target.id=='stems' for target in node.targets))
for stem in stems:
    previous=stem.replace('v19','v38')
    text=(base/previous).read_text(encoding='utf-8').replace('v38','v39').replace('V38','V39')
    if stem.endswith('startup_20261008.py'):
        needle='records={}\n'
        assert text.count(needle)==1
        text=text.replace(needle,"modules['avoidance.fast_connected_planner_candidate']='src/aerothon_avoidance/avoidance/avoidance/fast_connected_planner_candidate.py'\n"+needle,1)
    if stem.endswith('qualification_20261008.py'):
        assert 'assert len(startup) == 11' in text
        text=text.replace('assert len(startup) == 11','assert len(startup) == 12',1)
    if stem.startswith('run_v19_qualification_gates'):
        text=text.replace('reliability_reduced_v37_targeted_20261008/report.json','reliability_reduced_v38_targeted_20261008/report.json')
        text=text.replace('V37 targeted trials safely closed','V38 targeted trials safely closed')
        needle="subprocess.run(['bash',str(base/'run_reduced_v39_full_offline_20261008.sh')],check=True,cwd=root)"
        assert text.count(needle)==1
        text=text.replace(needle,
            "print('Targeted navigation PASS; running short native return regression before the full offline suite',flush=True)\n"
            "subprocess.run(['bash',str(base/'run_reduced_v39_focused_split_20261009.sh')],check=True,cwd=root)\n"+needle,1)
        text=text.replace('before full offline/native/campaign','before focused native/offline/full native/campaign')
    (base/previous.replace('v38','v39')).write_text(text,encoding='utf-8',newline='\n')

source=root/'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008/onboard.jsonl'
rows=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
row=next(item for item in rows if item.get('mission')=='RETURN_CORRIDOR')
approach=next(item for item in rows if item.get('mission')=='GATE_CROSSING' and row['stamp']-30<item['stamp']<row['stamp'])
pose=row['pose']['data']['pose'];position=pose['position'];q=pose['orientation']
entry=dict(x=position['x'],y=position['y'],alt=position['z'],
    yaw=math.atan2(2*(q['w']*q['z']+q['x']*q['y']),1-2*(q['y']**2+q['z']**2)),
    source=str(source.relative_to(root)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    captured_stamp=row['stamp'],purpose='Operator-only focused return start from failed native FCU entry; no world/truth input to avoidance')
point=approach['pose']['data']['pose']['position']
entry['approach']=dict(x=point['x'],y=point['y'],captured_stamp=approach['stamp'])
(base/'return_entry_split_v38_s20261003_20261009.json').write_text(json.dumps(entry,indent=2))
assert 'v24.18.0' in (base/'run_reduced_v39_full_offline_20261008.sh').read_text()
assert '--reduced-scope' in (base/'run_reduced_v39_full_offline_20261008.sh').read_text()
assert '--rtf 1' in (base/'run_reduced_v39_campaign_20261008.sh').read_text()
print('V39 gates prepared: five normal-timing targeted flights, native return replay, one reduced offline suite, five full native acceptances, 96-case campaign')

