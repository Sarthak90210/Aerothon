"""Read recorded onboard stage timing without changing acceptance evidence."""
import json, sys
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(line) for line in (out / 'onboard.jsonl').open()]
stages = []
for r in rows:
    phase = r.get('mission', '')
    if not stages or stages[-1]['phase'] != phase:
        stages.append(dict(phase=phase, start=r['stamp'], end=r['stamp']))
    stages[-1]['end'] = r['stamp']
for s in stages:
    s['duration_s'] = round(s['end'] - s['start'], 3)
print(json.dumps(stages, indent=2))
summary = json.loads((out / 'summary.json').read_text())
print('Acceptance failures:', summary['failures'])
sys.exit(0 if summary['acceptance_pass'] else 1)
