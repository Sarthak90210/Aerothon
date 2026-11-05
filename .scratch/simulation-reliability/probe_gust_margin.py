"""Minimized real controller loop; fixture truth is evaluation only."""
import argparse
import json
from pathlib import Path
import sys
import inspect
import textwrap
import hashlib
from types import MethodType

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root/'sim'))
import test_corridor_stress as stress
import test_slalom_traverse as slalom

p = argparse.ArgumentParser()
p.add_argument('--seed', type=int, required=True)
p.add_argument('--kind', choices=('dirty', 'late'), required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--delay', type=float, default=0.)
p.add_argument('--anticipate-delay', action='store_true')
p.add_argument('--raw-path', action='store_true')
p.add_argument('--rate-filter',type=float,default=0.)
p.add_argument('--cost-floor',type=float,default=0.)
args = p.parse_args()
assert not args.out.exists(), 'Preserve original probe'
case = stress.SplitLaneStressTests('test_gusty_crosswind')
case.setUpClass()
case.setUp()
if args.cost_floor:
    method=case.node._planner.plan.__func__;code=textwrap.dedent(inspect.getsource(method));old='max(0.05, float(d)-self.clearance)';assert code.count(old)==1
    code=code.replace(old,f'max({args.cost_floor!r}, float(d)-self.clearance)');namespace=dict(method.__globals__);exec(compile(code,'<diagnostic clearance cost>','exec'),namespace)
    case.node._planner.plan=MethodType(namespace['plan'],case.node._planner)
if args.rate_filter:
    method=case.node._compensated.__func__;code=textwrap.dedent(inspect.getsource(method))
    old='self._wind_rate_world += (rate-self._wind_rate_world)*f'
    assert code.count(old)==1
    code=code.replace(old,f'self._wind_rate_world += (rate-self._wind_rate_world)*min(1.,span/{args.rate_filter!r})')
    namespace=dict(method.__globals__);exec(compile(code,'<diagnostic rate filter>','exec'),namespace)
    case.node._compensated=MethodType(namespace['_compensated'],case.node)
if args.anticipate_delay:
    # Local diagnostic prototype, leaving the running full-suite source intact.
    method = case.node._compensated.__func__
    code = textwrap.dedent(inspect.getsource(method))
    old = "prediction = float(self._g('vel_response_s'))"
    assert code.count(old) == 1
    code = code.replace(old, old + " + float(self._g('vel_command_delay_s'))")
    namespace = dict(method.__globals__)
    exec(compile(code, '<diagnostic transport forecast>', 'exec'), namespace)
    case.node._compensated = MethodType(namespace['_compensated'], case.node)
if args.raw_path:
    method = case.node._planner.plan.__func__
    code = textwrap.dedent(inspect.getsource(method))
    old = "path, k = [raw[0]], 0"
    assert code.count(old) == 1
    code = code.replace(old, "self.path, self.reason = raw, 'diagnostic unsimplified path'\n    return raw\n    " + old)
    namespace = dict(method.__globals__)
    exec(compile(code, '<diagnostic raw lidar path>', 'exec'), namespace)
    case.node._planner.plan = MethodType(namespace['plan'], case.node._planner)
rows = []
original = case.node._publish

def capture(*a, **kw):
    original(*a, **kw)
    x, y = case.node._pos
    truth = min(slalom.gap_to(x, y, r) for r in slalom.WALLS+slalom.BLOCKS)
    rows.append(dict(stamp=case.node._now(), pose=[x,y],
                     independent_clearance_m=truth,
                     detail=case.node.last_detail))

case.node._publish = capture
passed = False
try:
    options = dict(corrupt=stress.dirty_lidar(args.seed)) if args.kind == 'dirty' else dict(scan_delay_s=.15)
    options['command_delay_s'] = args.delay
    case._through(drift=stress.WindDrift(seed=args.seed), **options)
    passed = True
except AssertionError as e:
    failure = str(e)
finally:
    report = dict(seed=args.seed, kind=args.kind, command_delay_s=args.delay,
                  source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py',root/'src/aerothon_avoidance/avoidance/avoidance/local_planner.py',root/'sim/test_slalom_traverse.py',root/'sim/test_corridor_stress.py',Path(__file__))},
                  physical_command_basis='body velocity and yaw queued; earth conversion at receipt',
                  diagnostic_transport_forecast=args.anticipate_delay, passed=passed,
                  diagnostic_raw_path=args.raw_path,
                  diagnostic_rate_filter_s=args.rate_filter,
                  diagnostic_cost_floor=args.cost_floor,
                  failure=None if passed else failure, rows=rows,
                  source='offline fixture evaluation; not drone input')
    args.out.write_text(json.dumps(report)+'\n')
    print(json.dumps(dict(passed=passed, minimum_clearance_m=min(r['independent_clearance_m'] for r in rows),
                         records=len(rows), failure=report['failure'])))
    case.tearDown()
    case.tearDownClass()
raise SystemExit(0 if passed else 1)
