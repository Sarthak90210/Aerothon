"""Run the receipt regression on the exact archived publication method."""
import ast,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'sim'));sys.path.insert(0,str(root/'src/aerothon_avoidance/avoidance'))
import avoidance.velocity_controller as module
archive=root/'logs/reliability_render_my_world_s20261003_gustfix_20261006/recorded_source.zip'
with zipfile.ZipFile(archive) as z:source=z.read('source/src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py').decode()
cls=next(v for v in ast.parse(source).body if isinstance(v,ast.ClassDef) and v.name=='VelocityController')
method=next(v for v in cls.body if isinstance(v,ast.FunctionDef) and v.name=='_publish')
namespace=dict(module.__dict__);exec(compile(ast.get_source_segment(source,method),'<exact archived publication>','exec'),namespace)
module.VelocityController._publish=namespace['_publish']
import pytest
raise SystemExit(pytest.main(['sim/test_yaw_motion_certification.py','-q']))
