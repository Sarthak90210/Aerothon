"""One-variable compensation probes, retaining real queue and clearance checks."""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--policy', choices=('no_rate', 'half_rate', 'velocity_feedback'), required=True)
parser.add_argument('--kind', choices=('dirty', 'late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
method = case.node._compensated.__func__
code = textwrap.dedent(inspect.getsource(method))
if compensation_policy in ('no_rate','half_rate'):
    old = "prediction = float(self._g('vel_response_s'))"
    assert code.count(old) == 1
    code = code.replace(old,"prediction = 0.0" if compensation_policy == 'no_rate' else "prediction = .5*float(self._g('vel_response_s'))")
else:
    old = "output = desired-compensation+feedback"
    assert code.count(old) == 1
    replacement = ''' + repr('''if self._response_known:
        future = self._expect_world.copy()
        delay = float(self._g('vel_command_delay_s'))
        tau = float(self._g('vel_response_s'))
        at = measured_t
        while at < now+delay-1e-9:
            end = min(at+.05,now+delay)
            future += (self._effective_command((at+end)/2)-future)*min(1.,(end-at)/tau)
            at = end
        predicted = np.array([[c,s],[-s,c]]) @ (future+self._wind_world+(now+delay-measured_t)*self._wind_rate_world)
        correction = .3*(desired-predicted)
        correction *= min(1.,.8/max(1e-9,float(np.linalg.norm(correction))))
        feedback += correction
    output = desired-compensation+feedback''') + '''
    code = code.replace(old,replacement)
namespace = dict(method.__globals__)
exec(compile(code,'<compensation-only diagnostic>','exec'),namespace)
case.node._compensated = MethodType(namespace['_compensated'],case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle, hook + '\n' + needle)
source = source.replace('report = dict(seed=args.seed,',
    'report = dict(diagnostic_compensation_policy=compensation_policy,probe_template_sha256=template_hash,seed=args.seed,')
sys.argv = [str(template), '--seed', str(args.seed), '--kind', args.kind,
            '--delay', '.4', '--out', args.out]
exec(compile(source, str(template), 'exec'), dict(
    __file__=str(Path(__file__).resolve()), __name__='__main__',
    compensation_policy=args.policy,
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
