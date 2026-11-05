"""Re-run the unchanged V25 publication seam with the final normal budget."""
import ast,hashlib,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path[:0]=[str(root/'sim'),str(root/'src/aerothon_avoidance/avoidance')]
import avoidance.velocity_controller as module
import pytest
name='src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
snapshot=root/'.scratch/reduced_scope_v25_candidate_20261008'
manifest=json.loads((snapshot/'source_manifest.json').read_text())
raw=(snapshot/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest[name]
tree=ast.parse(raw);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_publish')
namespace=dict(module.__dict__);exec(compile(ast.Module(body=[method],type_ignores=[]),str(snapshot/name),'exec'),namespace)
module.VelocityController._publish=namespace['_publish']
raise SystemExit(pytest.main(['sim/test_zero_queue_response_uncertainty.py','-q']))
