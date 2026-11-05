"""Separate repeated mission phases using closed recorded FCU samples."""
import json, math, sys
from pathlib import Path

run = Path(sys.argv[1])
rows = [json.loads(line) for line in (run / 'onboard.jsonl').open()]
phases = []
previous = None
for row in rows:
    state = row.get('mission')
    if previous is None or state != previous.get('mission'):
        phases.append(dict(state=state, start_s=row['stamp'], end_s=row['stamp'],
                           captured_interval_s=0., low_speed_s=0., distance_m=0.))
    phase = phases[-1]
    phase['end_s'] = row['stamp']
    if previous is not None and state == previous.get('mission'):
        dt = row['stamp'] - previous['stamp']
        v = (row.get('velocity') or {}).get('data', {}).get('twist', {}).get('linear', {})
        if 0 < dt < 1 and all(k in v for k in ('x', 'y')):
            speed = math.hypot(v['x'], v['y'])
            phase['captured_interval_s'] += dt
            phase['distance_m'] += speed * dt
            phase['low_speed_s'] += dt if speed < .1 else 0.
    previous = row
result = dict(scope='Contiguous recorded phases; low speed alone does not identify a fault',
              phases=phases, qualification=False)
with (run / 'contiguous_phase_attribution_20261007.json').open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
