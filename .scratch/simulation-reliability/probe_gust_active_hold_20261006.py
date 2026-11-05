"""Scratch-only proactive position hold with fresh-observation release.

The observed-rate reserve is a diagnostic assumption, not a qualified bound
on future wind. Physical traversal and clearance checks remain unchanged.
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
import numpy as np
import math
standard_publish = case.node._publish
hold_target = None
hold_started = None
ready_since = None
hold_count = 0
def hold_publish(self,vx,vy,front,bearing,extra):
    global hold_target,hold_started,ready_since,hold_count
    if 'fault' not in extra:
        delay = float(self._g('vel_command_delay_s'))
        tau = float(self._g('vel_response_s'))
        available = float(self._planner.distances([(0,0)])[0])
        required = self._planner.clearance+.025+delay*float(np.linalg.norm(self._ground_world))+.5*float(np.linalg.norm(self._wind_rate_world))*(delay+tau)**2
        if hold_target is None and self._response_known and available < required+.05 and self._planner.segment_clear((0,0),(0,0)):
            hold_target = np.array(self._pos,dtype=float)
            hold_started = self._now()
            ready_since = None
            hold_count += 1
        if hold_target is not None:
            if available > required+.1 and float(np.linalg.norm(self._wind_innovation_world)) < .05:
                if ready_since is None:
                    ready_since = self._now()
            else:
                ready_since = None
            if ready_since is not None and self._now()-ready_since >= .5:
                hold_target = None
                self.state = 'CRUISE'
                self._progress_ref,self._progress_t = self._pos,self._now()
            else:
                delta = (hold_target-np.array(self._pos))*.8
                delta *= min(1.,.25/max(1e-9,float(np.linalg.norm(delta))))
                c,s = math.cos(self._yaw),math.sin(self._yaw)
                vx,vy = c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1]
                bearing = 0.
                self.state = 'ACTIVE_HOLD'
                self._blocked = 0
                self._backoff = 0
                self._progress_ref,self._progress_t = self._pos,self._now()
        extra = dict(extra,diagnostic_control_policy='observed-rate position hold',
                     diagnostic_hold_count=hold_count,
                     diagnostic_hold_target=None if hold_target is None else hold_target.tolist(),
                     diagnostic_margin_required_m=required)
    standard_publish(vx,vy,front,bearing,extra)
case.node._publish = MethodType(hold_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle, hook + '\n' + needle)
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='observed-rate position hold',probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template), '--seed', str(args.seed), '--kind', args.kind,
            '--delay', '.4', '--out', args.out]
exec(compile(source, str(template), 'exec'), dict(
    __file__=str(Path(__file__).resolve()), __name__='__main__',
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
