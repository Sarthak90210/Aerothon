"""Record the unchanged certificate against the actual delayed plant.

The extra records cannot affect commands. Simulator geometry is used only by
the existing independent grader. Each command stores its exact body vector,
observer state and certificate attempts for post-flight analysis.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind', choices=('dirty', 'late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
method = case.node._publish.__func__
code = textwrap.dedent(inspect.getsource(method))
code = code.replace("fresh = 'fault' not in extra", "self._scratch_certificate = []\\n    fresh = 'fault' not in extra")
code = code.replace("target = np.array(command)+wind", "trace = dict(command=list(map(float,command)), path=[], passed=False)\\n            self._scratch_certificate.append(trace)\\n            target = np.array(command)+wind")
code = code.replace("nxt = point+velocity*dt", "nxt = point+velocity*dt\\n                trace['path'].append([float(t+dt), *map(float,nxt), *map(float,velocity)])")
# The nested return has twelve spaces after dedenting the outer method.
old = '            return True\\n        if not motion_clear'
assert code.count(old) == 1
code = code.replace(old, "            trace['passed'] = True\\n            return True\\n        if not motion_clear")
namespace = dict(method.__globals__)
exec(compile(code, '<unchanged certificate recording>', 'exec'), namespace)
case.node._publish = MethodType(namespace['_publish'], case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle, hook+'\n'+needle)
old = 'detail=case.node.last_detail))'
assert source.count(old) == 1
source = source.replace(old, '''detail=case.node.last_detail,
                     exact_body_command=[case.sent[-1].velocity.x,case.sent[-1].velocity.y],
                     measured_yaw=case.node._yaw,
                     expected_actuator_world=case.node._expect_world.tolist(),
                     observed_ground_world=case.node._ground_world.tolist(),
                     wind_world=case.node._wind_world.tolist(),
                     wind_rate_world=case.node._wind_rate_world.tolist(),
                     certificate_attempts=case.node._scratch_certificate))''')
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='unchanged certificate recording',probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template), '--seed', str(args.seed), '--kind', args.kind,
            '--delay', '.4', '--out', args.out]
exec(compile(source, str(template), 'exec'), dict(
    __file__=str(Path(__file__).resolve()), __name__='__main__',
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
