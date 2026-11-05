"""Verify installed runtime resolves the exact frozen current decision files."""
import hashlib
import importlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
out=root/'logs/reliability_early_red_clipped_bearing_qualification_20261007'
manifest=json.loads((out/'source_manifest.json').read_text())
names={'mission_bt.mission_tree':'src/aerothon_mission/mission_bt/mission_bt/mission_tree.py',
       'mission_bt.search_braking':'src/aerothon_mission/mission_bt/mission_bt/search_braking.py',
       'mission_bt.mav_commander':'src/aerothon_mission/mission_bt/mission_bt/mav_commander.py',
       'perception_redzone.redzone_node':'src/aerothon_perception/perception_redzone/perception_redzone/redzone_node.py',
       'perception_redzone.partial_boundary':'src/aerothon_perception/perception_redzone/perception_redzone/partial_boundary.py'}
records={}
for name,path in names.items():
    module=importlib.import_module(name)
    actual=Path(module.__file__).resolve()
    assert actual==(root/path).resolve(),str(actual)
    sha=hashlib.sha256(actual.read_bytes()).hexdigest();assert sha==manifest[path]
    records[name]=dict(resolved_file=str(actual),sha256=sha,matches_frozen_source=True)
with (out/'installed_import_verification.json').open('x') as stream:
    json.dump(records,stream,indent=2)
print(json.dumps(dict(verified_modules=len(records),all_installed_runtime_imports_match_frozen_source=True)))
