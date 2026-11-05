"""Track the observed waypoint from predicted command-receipt position.

Use the existing cruise/braking travel gain and unchanged certificate. The
physical queue, camera-free lidar fixture and drift generation are unchanged.
No model parameter is fitted to the trial seed.
"""
import argparse
import hashlib
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--kind',choices=('dirty','late'),required=True)
parser.add_argument('--seed',type=int,required=True)
parser.add_argument('--out',required=True)
args = parser.parse_args()
template = Path(__file__).with_name('probe_gust_margin.py')
source = template.read_text()
hook = '''
import math
import numpy as np
standard_publish = case.node._publish
def receipt_publish(self,vx,vy,front,bearing,extra):
    if 'fault' not in extra and self.state=='CRUISE' and self._path_world and self._response_known:
        delay = float(self._g('vel_command_delay_s'))
        tau = float(self._g('vel_response_s'))
        actuator = self._ground_world-self._wind_world
        point = np.array(self._pos,dtype=float)
        at = 0.
        while at < delay-1e-9:
            span = min(.05,delay-at)
            target = self._effective_command(self._now()+at+.5*span)
            actuator += (target-actuator)*min(1.,span/tau)
            point += (actuator+self._wind_world+at*self._wind_rate_world)*span
            at += span
        gain = self.cruise/(float(self._g('brake_dist'))-float(self._g('stop_dist')))
        travel = gain*(np.array(self._path_world[0])-point)
        travel *= min(1.,self.cruise/max(1e-9,float(np.linalg.norm(travel))))
        c,s = math.cos(self._yaw),math.sin(self._yaw)
        vx,vy = c*travel[0]+s*travel[1],-s*travel[0]+c*travel[1]
        cap = float(self._g('max_lateral'))
        vy = max(-cap,min(cap,vy))
        bearing = math.atan2(vy,vx)
        extra = dict(extra,diagnostic_control_policy='predicted receipt-position path tracking',
                     diagnostic_receipt_position_world_m=point.tolist())
    standard_publish(vx,vy,front,bearing,extra)
case.node._publish = MethodType(receipt_publish,case.node)
'''
needle = 'rows = []\noriginal = case.node._publish'
assert source.count(needle)==1
source = source.replace(needle,hook+'\n'+needle)
source = source.replace('report = dict(seed=args.seed,',
    "report = dict(diagnostic_policy='predicted receipt-position path tracking',probe_template_sha256=template_hash,seed=args.seed,")
sys.argv = [str(template),'--seed',str(args.seed),'--kind',args.kind,'--delay','.4','--out',args.out]
exec(compile(source,str(template),'exec'),dict(
    __file__=str(Path(__file__).resolve()),__name__='__main__',
    template_hash=hashlib.sha256(template.read_bytes()).hexdigest()))
