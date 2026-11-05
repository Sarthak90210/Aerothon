"""Exercise the runtime recorder's actual harness selector without launching ROS."""
import ast
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('capture_runtime_configuration.py')
tree = ast.parse(source.read_text())
selector = next(node for node in tree.body if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'harness' for target in node.targets))
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
output = root / 'logs/example_owned_output'
namespace = dict(Path=Path, __file__=str(source), out=output)
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)

def check(args, cwd, expected):
    process = dict(pid=100, ppid=90, group=100, args=args, cwd=str(cwd))
    namespace['processes'] = [process]
    exec(compile(ast.Module(body=[selector], type_ignores=[]), str(source), 'exec'), namespace)
    actual = namespace['harness'] is process
    assert actual is expected, f'Scope mismatch: expected {expected}, actual {actual}, args={args}'

script = root / 'scripts/run_recorded_acceptance.sh'
check(['bash', 'scripts/run_recorded_acceptance.sh', 'sim/worlds/shipped.json', '20261003',
       'logs/example_owned_output', 'logs/calibration.json'], root, True)
check(['/usr/bin/bash', 'scripts/run_recorded_acceptance.sh', 'sim/worlds/shipped.json', '20261003',
       str(output), 'logs/calibration.json'], root, True)
check(['bash', str(script), 'world.json', '20261003', str(output), 'profile.json'], root, True)
check(['bash', str(script), 'world.json', '20261003', str(output)+'_other', 'profile.json'], root, False)
check(['bash', 'scripts/run_recorded_acceptance.sh', 'world.json', '20261003',
       'logs/example_owned_output', 'profile.json'], root/'.scratch/another_checkout', False)
check(['bash', 'scripts/run_recorded_acceptance.sh', 'world.json', '20261003'], root, False)
check(['python3', 'scripts/run_recorded_acceptance.sh', 'world.json', '20261003', str(output), 'profile.json'], root, False)
check(['bash', str(root/'.scratch/another_checkout/scripts/run_recorded_acceptance.sh'),
       'world.json', '20261003', str(output), 'profile.json'], root, False)
print('PASS 8 owned-harness scope cases, including actual absolute-output caller')
