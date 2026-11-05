"""Separate release starvation from motion or clearance failure."""
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[2]
capture = root/'logs/reliability_gust_dirty_calm_empirical_viability_20261007.json'
rows = json.loads(capture.read_text())['rows']
counts = dict(eligible=0,speed_too_low=0,queue_not_clear=0,no_samples=0,ground_too_fast=0)
longest = 0.
started = None
for row in rows:
    d = row['detail']
    samples = d.get('diagnostic_error_samples',0)>=8
    speed = d.get('diagnostic_travel_speed_mps',0)>=.8/12
    queue = d.get('diagnostic_queue_clear',False)
    ground = d.get('ground_velocity_world_mps')
    slow = ground is not None and math.hypot(*ground)<=.8/12
    counts['speed_too_low'] += not speed
    counts['queue_not_clear'] += not queue
    counts['no_samples'] += not samples
    counts['ground_too_fast'] += not slow
    if samples and speed and queue:
        counts['eligible'] += 1
        if started is None:
            started = row['stamp']
        longest = max(longest,row['stamp']-started)
    else:
        started = None
result = dict(counts=counts,rows=len(rows),longest_uninterrupted_eligible_s=longest)
out = root/'.scratch/simulation-reliability/empirical_viability_calm_release_starvation_20261007.json'
assert not out.exists()
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
