"""Evaluation-only realized seed envelope; no ROS imports or controller edits."""
import ast
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.scratch/qualified_navigation_baseline_20261006/sim/test_corridor_stress.py'
raw = SOURCE.read_bytes()
tree = ast.parse(raw)
wind_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WindDrift')
space = dict(np=np, math=math, RHO=1.2)
exec(compile(ast.Module(body=[wind_class], type_ignores=[]), str(SOURCE), 'exec'), space)
results = []
for seed in range(6):
    wind = space['WindDrift'](seed=seed)
    rows = []
    previous = np.zeros(2)
    for tick in range(3000):
        t = tick * .05
        residual = np.array(wind(t))
        rate = (residual-previous)/.05
        speed = wind.mean + wind.gust*math.sin(2*math.pi*t/wind.period+wind.phase)
        actual_wind = wind.u*speed + wind.ou
        rows.append(dict(stamp=t, wind_norm_mps=float(np.linalg.norm(actual_wind)),
                         turbulence_norm_mps=float(np.linalg.norm(wind.ou)),
                         residual_norm_mps=float(np.linalg.norm(residual)),
                         residual_rate_norm_mps2=float(np.linalg.norm(rate))))
        previous = residual
    def maxima(prefix):
        return {key:max(prefix,key=lambda r:r[key]) for key in rows[0] if key != 'stamp'}
    results.append(dict(seed=seed, first_20_s=maxima(rows[:400]), full_150_s=maxima(rows)))
report = dict(source=str(SOURCE), source_sha256=hashlib.sha256(raw).hexdigest(),
              kind='Unflown evaluation-only disturbance draws', ticks_per_seed=3000,
              dt_s=.05, seeds=results,
              limits=['Gaussian OU draws are not bounded by these finite sampled maxima.',
                      'The first residual derivative includes the initial trim-to-gust transient.',
                      'No simulator disturbance draw or derivative is fed to drone decision logic.',
                      'This does not demonstrate that every sampled trajectory is unavoidable.'])
out = ROOT / '.scratch/simulation-reliability/wind_draw_characterization_20261006.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(out=str(out),summary=[dict(seed=r['seed'],
    first_20_s={k:v[k] for k,v in r['first_20_s'].items()},
    full_150_s={k:v[k] for k,v in r['full_150_s'].items()}) for r in results]),indent=2))
