"""Expand the new candidate only after all three preserved failures pass."""
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[2]
focus = root/'logs/reliability_capture_inbox_field23_navigation_20261007'
while not (focus/'closed_batch_review.json').exists():
    status = root/'logs/reliability_capture_inbox_field23_closure_owned_20261007/status.json'
    if status.exists():
        value = json.loads(status.read_text())
        if value['state'] in ('FAILED', 'COMPLETED') and not (focus/'closed_batch_review.json').exists():
            raise RuntimeError('Focused evidence closure ended without verified review')
    time.sleep(5)
for directory, count in (('reliability_capture_inbox_field1_navigation_20261007', 1),
                         ('reliability_capture_inbox_field23_navigation_20261007', 2)):
    closed = json.loads((root/'logs'/directory/'closed_batch_review.json').read_text())
    assert len(closed['trials']) == count and closed['all_trials_disarmed'] and closed['source_unchanged']
    if not all(trial['navigation_pass'] and trial['sampling_reserve_pass'] for trial in closed['trials']):
        print('Focused repeat failed; remaining-case expansion withheld. All failures remain recorded.', flush=True)
        raise SystemExit(1)
code = subprocess.run(['/usr/bin/python3', '.scratch/simulation-reliability/run_capture_inbox_remaining_seven_20261007.py'], cwd=root).returncode
# Verify and retain failed cases too. A failed mission cannot be discarded.
closure = subprocess.run(['/usr/bin/python3', '.scratch/simulation-reliability/close_capture_inbox_remaining_seven_20261007.py'], cwd=root).returncode
raise SystemExit(code or closure)
