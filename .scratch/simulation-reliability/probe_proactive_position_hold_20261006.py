"""Scratch-only early position hold through the unchanged motion certificate.

The target is the aircraft's measured current position. This diagnostic never
claims corridor completion. Clearance truth is read only after the flight.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--kind',choices=('dirty','late'),required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--out',required=True)
args=parser.parse_args()
template=Path(__file__).with_name('probe_gust_margin.py')
source=template.read_text()
hook='''
import numpy as np
import math
original_fly=case.fly
def limited_fly(*a,**kw):
    kw['max_t']=20.
    return original_fly(*a,**kw)
case.fly=limited_fly
standard_publish=case.node._publish
hold_target=None
def proactive_publish(self,vx,vy,front,bearing,extra):
    global hold_target
    if 'fault' not in extra:
        delay=float(self._g('vel_command_delay_s'))
        tau=float(self._g('vel_response_s'))
        # The existing derivative cap is a diagnostic uncertainty envelope,
        # not a measured hardware wind bound. Stop entry when its projected
        # displacement no longer fits beyond the unchanged sampling reserve.
        needed=self._planner.clearance+.025+delay*float(np.linalg.norm(self._ground_world))+.5*.8*(delay+tau)**2
        available=float(self._planner.distances([(0,0)])[0])
        if hold_target is None and available<needed and self._planner.segment_clear((0,0),(0,0)):
            hold_target=np.array(self._pos,dtype=float)
        if hold_target is not None:
            delta=(hold_target-np.array(self._pos))*.8
            delta*=min(1.,.25/max(1e-12,float(np.linalg.norm(delta))))
            c,s=math.cos(self._yaw),math.sin(self._yaw)
            vx,vy=c*delta[0]+s*delta[1],-s*delta[0]+c*delta[1]
            bearing=0.
            extra=dict(extra,diagnostic_control_policy='proactive measured-position hold',
                       diagnostic_hold_target_world_m=hold_target.tolist(),diagnostic_needed_clearance_m=needed)
    standard_publish(vx,vy,front,bearing,extra)
case.node._publish=MethodType(proactive_publish,case.node)
'''
needle='rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source=source.replace(needle,hook+'\n'+needle)
source=source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_control_policy='proactive measured-position hold',diagnostic_duration_s=20.,"+
    "minimum_actual_clearance_m=min(slalom.gap_to(case.closest_detail['x'],case.closest_detail['y'],r) for r in slalom.WALLS+slalom.BLOCKS),"+
    "probe_template_sha256=probe_template_hash,seed=args.seed,")
sys.argv=[str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','0.4','--out',args.out]
exec(compile(source,str(template),'exec'),dict(__file__=str(Path(__file__).resolve()),__name__='__main__',
    probe_template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
