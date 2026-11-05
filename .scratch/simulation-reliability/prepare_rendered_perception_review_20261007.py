"""Prepare exact review files; do not mutate an active rendered producer."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
here=Path(__file__).parent
out=root/'logs/reliability_rendered_perception_review_patch_20261007';out.mkdir(exist_ok=False)
changes=[]
def method(source,cls,name,replacement):
    tree=ast.parse(source)
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    node=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1])+''.join('    '+line if line.strip() else line for line in replacement.splitlines(keepends=True))+''.join(lines[node.end_lineno:])
def save(name,after):
    target=root/name;before=target.read_text() if target.exists() else ''
    ast.parse(after)
    label=name.replace('/','__')
    candidate=out/(label+'.candidate');candidate.write_bytes(after.encode())
    if target.exists():(out/(label+'.before')).write_bytes(target.read_bytes())
    (out/(label+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
    changes.append(dict(path=name,base_sha256=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
        candidate=candidate.relative_to(root).as_posix(),candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest()))
red='src/aerothon_perception/perception_redzone/perception_redzone/'
source=(root/(red+'redzone_node.py')).read_text()
replacement=(root/'logs/reliability_provisional_red_entry_after_retry2_20261007/source_override/candidate_on_image.py').read_text()
source=method(source,'RedZoneNode','on_image',replacement)
source=source.replace('NOT_VISIBLE = "NOT_VISIBLE"','from perception_redzone.partial_boundary import partial_boundaries\n\nNOT_VISIBLE = "NOT_VISIBLE"')
save(red+'redzone_node.py',source)
save(red+'partial_boundary.py',(here/'partial_red_boundary_candidate_20261007.py').read_text())
mission='src/aerothon_mission/mission_bt/mission_bt/'
source=(root/(mission+'mav_commander.py')).read_text()
replacement=(root/'logs/reliability_provisional_red_entry_after_retry2_20261007/source_override/candidate_on_redzone.py').read_text()
save(mission+'mav_commander.py',method(source,'Mav','_on_redzone',replacement))
source=(root/(mission+'mission_tree.py')).read_text()
source=method(source,'LawnmowerSearch','update',(root/'logs/reliability_search_braking_after_20261007/candidate_update.py').read_text())
source=method(source,'AlignToBanner','_dwell',(root/'logs/reliability_clipped_banner_bearing_after_20261007/candidate_dwell.py').read_text())
source='from mission_bt.search_braking import SearchBrakingGate\n'+source if not source.startswith('#!') else source.replace('import math','from mission_bt.search_braking import SearchBrakingGate\nimport math',1)
# Reset pending braking whenever the search leaf is re-entered.
tree=ast.parse(source);owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LawnmowerSearch')
node=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='initialise')
lines=source.splitlines(keepends=True)
lines.insert(node.lineno,"        self._search_braking_gate=SearchBrakingGate()\n        self._streamed_search_goal=None\n")
save(mission+'mission_tree.py',''.join(lines))
save(mission+'search_braking.py',(here/'search_braking_candidate_20261007.py').read_text())
for name in ('test_search_braking_20261007.py','test_provisional_red_entry_20261007.py'):
    save('sim/'+name,(here/name).read_text())
report=dict(production_modified=False,changes=changes,required_checks=dict(search='130 passed',partial_red='94 passed',clipped_bearing='139 passed',red_qr_cases=432),
    next_suite='full offline on integrated source',next_rendered='split corridor seed 20261003 then rotated and standard pair',
    required_corridor_clearance_m=.70,required_exclusion_clearance_m=1.50,hardware_qualified=False)
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(prepared_files=len(changes),production_modified=False)))
