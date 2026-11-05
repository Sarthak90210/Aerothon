"""Read inferred decisions from the existing onboard recording only."""
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
for line in (out/'onboard.jsonl').open():
    try:
        row = json.loads(line)
    except ValueError:
        continue
    observation = row.get('observation', {})
    if row.get('mission') == 'WINCH_DROP' and observation.get('state') == 'DONE':
        print(json.dumps(dict(recorded_stamp=row['stamp'], observation=observation), indent=2))
        break
else:
    print('No active delivery DONE recorded yet')
