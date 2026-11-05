"""A sensor-based certificate accepts a command whose delayed plant breaches.

Compile only the current production certificate. The observed wall is 0.750 m
away. A linear wind velocity change of 0.8 m/s2 is held constant over the next
0.4 s. No corrective command can arrive during that interval. This checks a
missing physical assumption, rather than claiming that future wind is known
by the onboard controller.
"""
import ast
import argparse
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--extra-feedthrough',action='store_true')
args = parser.parse_args()
path = root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'
tree = ast.parse(path.read_text())
method = next(node for node in ast.walk(tree)
              if isinstance(node, ast.FunctionDef) and node.name == 'motion_clear')
parameters = dict(vel_command_delay_s=.4, vel_response_s=.6,
                  braking_accel_mps2=.5)
wall_distance = .750
seen = []

def segment_clear(start, end):
    # This is a single fully observed flat wall, equivalent to a lidar map.
    seen.append(tuple(end))
    return wall_distance-max(start[1],end[1]) >= .725

self = SimpleNamespace(
    _g=parameters.__getitem__, _now=lambda:0.,
    _command_known=lambda stamp:True,
    _effective_command=lambda stamp:np.zeros(2),
    _planner=SimpleNamespace(segment_clear=segment_clear))
namespace = dict(self=self,np=np,math=math,ground=np.zeros(2),wind=np.zeros(2),
                 wind_rate=np.array([0.,.8]),rotation=np.eye(2),receipt_turn=0.)
exec(compile(ast.Module(body=[method],type_ignores=[]),str(path),'exec'),namespace)
accepted = namespace['motion_clear']((0.,-.8))
if args.extra_feedthrough:
    code = ast.unparse(method)
    code = code.replace('def motion_clear(command):','def motion_clear_external(command):')
    needle = '        velocity += change'
    assert code.count(needle)==1
    code = code.replace(needle,'        if t<delay+tau:\n            change += dt*wind_rate\n'+needle)
    exec(compile(code,'<additional drift feedthrough certificate>','exec'),namespace)
    accepted = accepted and namespace['motion_clear_external']((0.,-.8))
physical_displacement = sum(.8*t*.05 for t in np.arange(0.,.399999,.05))
physical_clearance = wall_distance-physical_displacement
print(dict(source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
           prototype_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           additional_external_drift_conjunct=args.extra_feedthrough,
           accepted=accepted,maximum_predicted_toward_wall_m=max(p[1] for p in seen),
           actual_unavoidable_displacement_m=physical_displacement,
           actual_clearance_after_delay_m=physical_clearance,
           actual_command_basis='zero packets pending; corrective body command arrives at 0.4 s'))
assert not accepted or physical_clearance >= .7, (
    'Accepted certificate underestimates unavoidable wind displacement before command receipt')
