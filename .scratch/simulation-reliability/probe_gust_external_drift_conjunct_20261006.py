"""Add a physical drift forecast conjunct without removing the old certificate.

Every command passes both the existing full motion certificate and a variant
with measured drift acceleration entering ground velocity directly. This is
a diagnostic point forecast, not a qualified uncertainty envelope.
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
start = code.index('        def motion_clear(command):')
end = code.index('        if not motion_clear((vx,vy)):')
original_certificate = code[start:end]
external_certificate = original_certificate.replace('def motion_clear(command):','def motion_clear_external(command):')
needle = '                velocity += change'
assert external_certificate.count(needle) == 1
external_certificate = external_certificate.replace(needle,
    '                if t<delay+tau:\\n                    change += dt*wind_rate\\n'+needle)
new = original_certificate.replace('def motion_clear(command):','def motion_clear_legacy(command):')+external_certificate
new += '        def motion_clear(command):\\n            return motion_clear_legacy(command) and motion_clear_external(command)\\n'
code = code[:start]+new+code[end:]
namespace = dict(method.__globals__)
exec(compile(code,'<additional external drift certificate>', 'exec'),namespace)
case.node._publish = MethodType(namespace['_publish'],case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle,hook+'\n'+needle)
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='original AND external drift feedthrough certificate',probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template),'--seed',str(args.seed),'--kind',args.kind,
            '--delay','.4','--out',args.out]
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
