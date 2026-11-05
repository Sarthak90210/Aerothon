"""Post-flight test of drift feedthrough over the unavoidable delay interval.

Reproduce physical drift only as independent evaluation. Compare point
forecasts from the recorded onboard estimate. No future evaluation samples
are supplied to the controller.
"""
import ast
import hashlib
import json
import math
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[2]
capture = root/'logs/reliability_gust_dirty_certificate_trace_20261006.json'
out = root/'.scratch/simulation-reliability/gust_dirty_direct_velocity_forecast_20261006.json'
report = json.loads(capture.read_text())
rows = report['rows']
fixture = root/'sim/test_corridor_stress.py'
tree = ast.parse(fixture.read_text())
wind_class = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WindDrift')
namespace = dict(np=np,math=math,RHO=1.2)
exec(compile(ast.Module(body=[wind_class],type_ignores=[]),str(fixture),'exec'),namespace)
drift = namespace['WindDrift'](seed=report['seed'])
physical_wind = [np.zeros(2)]
for row in rows[:-1]:
    physical_wind.append(np.array(drift(row['stamp'])))

def received_command(stamp):
    candidate = None
    for row in rows:
        if row['stamp'] <= stamp-.4+1e-9:
            candidate = row
        else:
            break
    if candidate is None:
        return np.zeros(2)
    receipt = min(rows,key=lambda r:abs(r['stamp']-(candidate['stamp']+.4)))
    c,s = math.cos(receipt['measured_yaw']),math.sin(receipt['measured_yaw'])
    vx,vy = candidate['exact_body_command']
    return np.array([c*vx-s*vy,s*vx+c*vy])

actor = np.zeros(2)
physical_ground_error = []
physical_actor = []
for i,row in enumerate(rows):
    physical_actor.append(actor.copy())
    physical_ground_error.append(float(np.linalg.norm(
        actor+physical_wind[i]-np.array(row['observed_ground_world']))))
    actor += (received_command(row['stamp'])-actor)*(.05/.6)
evaluations = []
for i,row in enumerate(rows[:-8]):
    if not row['detail']['disturbance_estimate_valid']:
        continue
    base = np.array(row['observed_ground_world'])
    feed = base.copy()
    oracle_actor = physical_actor[i].copy()
    original_point = np.zeros(2)
    feed_point = np.zeros(2)
    oracle_point = np.zeros(2)
    wind = np.array(row['wind_world'])
    rate = np.array(row['wind_rate_world'])
    for step in range(8):
        t = .05*step
        command = received_command(row['stamp']+t)
        base += (command+wind+t*rate-base)*(.05/.6)
        feed += (command+wind+t*rate-feed)*(.05/.6)+.05*rate
        oracle_actor += (command-oracle_actor)*(.05/.6)
        original_point += base*.05
        feed_point += feed*.05
        oracle_point += (oracle_actor+physical_wind[i+step+1])*.05
    actual = np.array(rows[i+8]['pose'])-np.array(row['pose'])
    evaluations.append(dict(stamp=row['stamp'],
        observed_rate_world=row['wind_rate_world'],
        original_error_m=float(np.linalg.norm(original_point-actual)),
        direct_feedthrough_error_m=float(np.linalg.norm(feed_point-actual)),
        oracle_physical_closure_error_m=float(np.linalg.norm(oracle_point-actual))))
result = dict(
    controller_sha256=report['source_sha256']['src/aerothon_avoidance/avoidance/avoidance/velocity_controller.py'],
    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
    capture_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),
    analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    source='post-flight evaluation only; oracle physical drift never supplied to controller',
    maximum_physical_ground_reconstruction_error_mps=max(physical_ground_error),
    samples=len(evaluations),
    original_maximum_error_m=max(r['original_error_m'] for r in evaluations),
    direct_feedthrough_maximum_error_m=max(r['direct_feedthrough_error_m'] for r in evaluations),
    oracle_maximum_physical_closure_error_m=max(r['oracle_physical_closure_error_m'] for r in evaluations),
    at_last_accepted_packet=next(r for r in evaluations if abs(r['stamp']-4.7)<1e-6),
    worst_original=sorted(evaluations,key=lambda r:r['original_error_m'],reverse=True)[:8],
    worst_direct_feedthrough=sorted(evaluations,key=lambda r:r['direct_feedthrough_error_m'],reverse=True)[:8])
assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('worst_original','worst_direct_feedthrough')}))
assert result['maximum_physical_ground_reconstruction_error_mps']<1e-5
assert result['oracle_maximum_physical_closure_error_m']<1e-5
