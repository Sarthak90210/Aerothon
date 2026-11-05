"""In-memory one-variable certificate probes; no production or sensor edits."""
import argparse
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--policy',choices=('terminal_raw_zero','delayed_terminal_hold','rate_alternatives'),required=True)
parser.add_argument('--kind',choices=('dirty','late'),required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--out',required=True)
args=parser.parse_args()
probe=Path(__file__).with_name('probe_gust_margin.py')
source=probe.read_text()
hook='''
method = case.node._publish.__func__
code = textwrap.dedent(inspect.getsource(method))
if prototype_policy == 'terminal_raw_zero':
    old = 'goal = np.zeros(2)'
    assert code.count(old) == 1
    code = code.replace(old, 'goal = wind+min(t,delay+tau)*wind_rate')
elif prototype_policy == 'delayed_terminal_hold':
    old = 'if t<delay+tau:'
    assert code.count(old) == 1
    code = code.replace(old, 'if t<2*delay+tau:')
elif prototype_policy == 'rate_alternatives':
    code = code.replace('def motion_clear(command):', 'def motion_clear_once(command):')
    old = '        if not motion_clear((vx,vy)):'
    assert code.count(old) == 1
    replacement = ''' + repr('''        def motion_clear(command):
            nonlocal wind_rate
            original_rate = wind_rate.copy()
            try:
                for hypothesis in (original_rate,np.zeros(2),-original_rate):
                    wind_rate = hypothesis
                    if not motion_clear_once(command):
                        return False
                return True
            finally:
                wind_rate = original_rate
        if not motion_clear((vx,vy)):''') + '''
    code = code.replace(old,replacement)
namespace = dict(method.__globals__)
exec(compile(code,'<one-variable terminal certificate prototype>','exec'),namespace)
case.node._publish = MethodType(namespace['_publish'],case.node)
'''
needle='rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source=source.replace(needle,hook+'\n'+needle)
source=source.replace('report = dict(seed=args.seed,','report = dict(diagnostic_terminal_policy=prototype_policy,seed=args.seed,')
sys.argv=[str(probe),'--seed',str(args.seed),'--kind',args.kind,'--delay','0.4','--out',args.out]
exec(compile(source,str(probe),'exec'),dict(__file__=str(Path(__file__).resolve()),__name__='__main__',prototype_policy=args.policy))
