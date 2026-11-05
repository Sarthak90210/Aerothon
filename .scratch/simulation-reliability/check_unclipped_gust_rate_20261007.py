"""Isolate observer derivative saturation, retaining sensors and physical delay."""
from pathlib import Path
base = Path(__file__).parent
source = (base / 'check_command_deadline_coupled_20261007.py').read_text()
source = source.replace('reliability_command_deadline_coupled_20261007',
                        'reliability_derivative_cap_1_6_coupled_20261007')
needle = 'summary=[]\n'
assert source.count(needle) == 1
hook = '''
import inspect,textwrap
method=velocity_controller.VelocityController._compensated
candidate=textwrap.dedent(inspect.getsource(method))
old="rate *= min(1.0,.8/max(1e-6,float(np.linalg.norm(rate))))"
assert candidate.count(old)==1
candidate=candidate.replace(old,"rate *= min(1.0,1.6/max(1e-6,float(np.linalg.norm(rate))))")
namespace=dict(method.__globals__)
exec(compile(candidate,'<isolated derivative saturation diagnostic>','exec'),namespace)
velocity_controller.VelocityController._compensated=namespace['_compensated']
(out/'candidate_compensation.py').write_text(candidate)
(out/'candidate_provenance.json').write_text(json.dumps(dict(
    reason='Prior recorded raw residual rate exceeds the hardcoded 0.8 cap; isolate that saturation only',
    candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
    derivative_cap_mps2=1.6, production_adopted=False,
    limitation='Diagnostic parameter, not a qualified future uncertainty bound',
    baseline_sha256=hashlib.sha256(Path(velocity_controller.__file__).read_bytes()).hexdigest())))
summary=[]
'''
source = source.replace(needle, hook)
exec(compile(source, str(base / 'check_command_deadline_coupled_20261007.py'), 'exec'))
