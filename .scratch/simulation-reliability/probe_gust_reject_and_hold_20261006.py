"""Permanently reject traversal when the original certificate first fails all.

Latch only the aircraft's measured current position after an uncertified raw
zero. Feed measured-position corrections through the untouched compensation
and certificate. There is no release rule or claim of mission completion.
The experiment checks whether early rejection can remain clear in the exact
physical delayed gust cases. It does not qualify a general disturbance bound.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind', choices=('dirty','late'), required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--duration', type=float, default=150.)
parser.add_argument('--out', required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
import math
import numpy as np
original_fly = case.fly
def bounded_fly(*a,**kw):
    kw['max_t'] = duration
    return original_fly(*a,**kw)
case.fly = bounded_fly
standard_publish = case.node._publish
hold_target = None
rejected_at = None
def rejected_publish(self,vx,vy,front,bearing,extra):
    global hold_target,rejected_at
    if 'fault' not in extra and hold_target is not None:
        correction = .8*(hold_target-np.array(self._pos))
        correction *= min(1.,.25/max(1e-9,float(np.linalg.norm(correction))))
        c,s = math.cos(self._yaw),math.sin(self._yaw)
        vx,vy = c*correction[0]+s*correction[1],-s*correction[0]+c*correction[1]
        bearing = 0.
        self._progress_ref,self._progress_t = self._pos,self._now()
        extra = dict(extra,diagnostic_control_policy='permanent rejection after uncertified braking',
                     diagnostic_rejected_at_s=rejected_at,
                     diagnostic_hold_target_world_m=hold_target.tolist())
    standard_publish(vx,vy,front,bearing,extra)
    if hold_target is None and self.last_detail.get('braking_clearance_available') is False:
        hold_target = np.array(self._pos,dtype=float)
        rejected_at = self._now()
case.node._publish = MethodType(rejected_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle) == 1
source = source.replace(needle,hook+'\n'+needle)
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='permanent rejection after uncertified braking',"+
    "diagnostic_duration_s=duration,diagnostic_rejected_at_s=rejected_at,"+
    "diagnostic_hold_target_world_m=None if hold_target is None else hold_target.tolist(),"+
    "minimum_actual_clearance_m=min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),"+
    "probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','.4','--out',args.out]
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',duration=args.duration,
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
