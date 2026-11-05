"""Same frozen-source scope, with ignored dependency trees pruned before traversal."""
import hashlib,json,os
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'sim'))
from campaign_record import source_manifest

def manifest():
    source_manifest.cache_clear()
    data={name.replace('\\','/'):sha for name,sha in source_manifest(root).items()}
    for directory in ('src','scripts','sim'):
        for base,dirs,files in os.walk(root/directory):
            dirs[:]=[name for name in dirs if name not in ('node_modules','dist','build','__pycache__')]
            for name in files:
                path=Path(base)/name
                if path.suffix in ('.xacro','.urdf','.png','.txt','.glb'):
                    data[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('capture_runtime_configuration.py','audit_decision_inputs.py',
                 'grade_focused_return.py','grade_focused_delivery.py'):
        path=Path(__file__).with_name(name)
        data[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    path=root/'logs/delivery_profile_20261005.json'
    data[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return data

if __name__=='__main__':
    frozen=json.loads((root/sys.argv[1]).read_text())
    actual=manifest()
    assert actual==frozen,dict(missing=list(frozen.keys()-actual.keys()),
        added=list(actual.keys()-frozen.keys()),changed=[name for name in frozen if actual.get(name)!=frozen[name]])
    print(json.dumps(dict(files=len(actual),exact_frozen_scope_match=True)))
