"""Run alignment regressions against archived methods without editing files."""
import ast
import sys
import zipfile
import pytest
import avoidance.velocity_controller as module

with zipfile.ZipFile(sys.argv[1]) as archive:
    source=archive.read('source/src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py').decode()
tree=ast.parse(source)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VelocityController')
for name in ('_compensated','_on_enable'):
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    namespace=vars(module).copy()
    exec(compile(ast.Module(body=[method],type_ignores=[]),'archived_bannerfix_controller','exec'),namespace)
    setattr(module.VelocityController,name,namespace[name])
raise SystemExit(pytest.main(['sim/test_fcu_velocity_sample_alignment.py','-q']))
