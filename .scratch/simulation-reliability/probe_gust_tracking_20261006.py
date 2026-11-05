"""One-variable in-memory controller experiments on the saved gust failures.

No production source or physical/sensor fixture is modified. Every experiment
retains the unchanged motion certificate and requires actual traversal.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--policy', choices=('slower_travel', 'distance_tracking',
                                         'disturbance_speed'), required=True)
parser.add_argument('--kind', choices=('dirty', 'late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--out', required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
import math
import numpy as np
original_publish = case.node._publish
if prototype_policy == 'slower_travel':
    case.node.cruise = .35
else:
    def tracked_publish(self, vx, vy, front, bearing, extra):
        if 'fault' not in extra and self.state == 'CRUISE':
            if prototype_policy == 'distance_tracking' and self._path_world:
                delta = np.array(self._path_world[0])-np.array(self._pos)
                delta *= .8
                speed = math.hypot(vx,vy)
                delta *= min(1.,speed/max(1e-9,float(np.linalg.norm(delta))))
                c,s = math.cos(self._yaw),math.sin(self._yaw)
                vx,vy = c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1]
            elif prototype_policy == 'disturbance_speed':
                scale = .4 if float(np.linalg.norm(self._wind_rate_world)) > .1 else 1.
                vx,vy = vx*scale,vy*scale
        original_publish(vx,vy,front,bearing,extra)
    case.node._publish = MethodType(tracked_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle, hook + '\n' + needle)
source = source.replace('report = dict(seed=args.seed,',
    'report = dict(diagnostic_policy=prototype_policy,probe_template_sha256=template_hash,seed=args.seed,')
sys.argv = [str(template), '--seed', str(args.seed), '--kind', args.kind,
            '--delay', '.4', '--out', args.out]
exec(compile(source, str(template), 'exec'), dict(
    __file__=str(Path(__file__).resolve()), __name__='__main__',
    prototype_policy=args.policy,
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
