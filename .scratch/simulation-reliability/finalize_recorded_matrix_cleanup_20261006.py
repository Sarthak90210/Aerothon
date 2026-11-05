"""Recheck only identities recorded by the cancelled matrix cleanup."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

job = Path(__file__).resolve().parents[2] / 'logs/reliability_navigation_baseline_matrix_owned_20261006'
spec = importlib.util.spec_from_file_location('owned', Path(__file__).with_name('launch_owned_job_20261006.py'))
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)
audit = owned.read_json(job / 'orphan_cleanup.json')

def state(record):
    if not owned.same_process(record):
        return 'gone'
    try:
        return Path(f"/proc/{record['pid']}/stat").read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        return 'gone'

records = list(audit['selected_processes'].values())
before = {str(record['pid']): state(record) for record in records}
for record in records:
    if state(record) not in ('gone', 'Z', 'X'):
        assert owned.same_process(record)
        os.kill(record['pid'], signal.SIGKILL)
time.sleep(1)
after = {str(record['pid']): state(record) for record in records}
active = [pid for pid, value in after.items() if value not in ('gone', 'Z', 'X')]
report = dict(before=before, after=after, active_owned_processes=active,
              note='Zombie entries are exited processes, cannot run or publish, and await parent reap')
owned.atomic_json(job / 'orphan_cleanup_final.json', report)
print(json.dumps(dict(active_owned_processes=active, exited_records=len(after)), indent=2))
assert not active
