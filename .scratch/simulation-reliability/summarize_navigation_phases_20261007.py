"""Summarise recorded phase durations without feeding evaluation into control."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
out = Path(sys.argv[1])
spans = defaultdict(lambda: [None, None, 0])
with (out/'track.csv').open() as handle:
    for row in csv.DictReader(handle):
        state = row.get('state')
        t = float(row['t_sim'])
        span = spans[state]
        if span[0] is None:
            span[0] = t
        span[1] = t
        span[2] += 1
print(json.dumps({state: dict(start=a, end=b, elapsed_s=round(b-a, 2), samples=count)
    for state, (a,b,count) in spans.items()}, indent=2))
