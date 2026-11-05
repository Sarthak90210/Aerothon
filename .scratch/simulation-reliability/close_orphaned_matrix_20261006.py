"""Close the verified, task-owned cancelled matrix and its escaped child groups."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

root = Path(__file__).resolve().parents[2]
job = root / 'logs/reliability_navigation_baseline_matrix_owned_20261006'
campaign = root / 'logs/reliability_navigation_baseline_matrix_20261006'
spec = importlib.util.spec_from_file_location('owned', Path(__file__).with_name('launch_owned_job_20261006.py'))
owned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned)
status = owned.read_json(job / 'status.json')
assert status['state'] == 'STOPPED'
record = status['command_process']
assert record['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip()

processes = {}
for path in Path('/proc').iterdir():
    if not path.name.isdigit():
        continue
    try:
        fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
        argv = (path / 'cmdline').read_bytes().split(b'\0')
        identity = owned.identity(int(path.name))
        processes[int(path.name)] = dict(identity=identity, ppid=int(fields[1]), argv=argv)
    except (FileNotFoundError, ProcessLookupError):
        continue
candidates = [pid for pid, process in processes.items()
    if process['identity']['pgid'] == record['pgid']
    and b'sim/run_navigation_campaign.py' in process['argv']
    and str(campaign).encode() in process['argv']]
assert len(candidates) == 1, 'Expected one specifically owned cancelled coordinator'
coordinator = candidates[0]
identity = processes[coordinator]['identity']
assert owned.same_process(identity)
os.kill(coordinator, signal.SIGSTOP)
selected = {coordinator}
while True:
    children = {pid for pid, process in processes.items() if process['ppid'] in selected}
    if children.issubset(selected):
        break
    selected.update(children)
records = {pid: processes[pid]['identity'] for pid in selected}
audit = dict(cancelled_coordinator=identity,
    selected_processes={str(pid): data for pid, data in records.items()},
    scope='Verified cancelled matrix and direct descendants captured before coordinator removal')
owned.atomic_json(job / 'orphan_cleanup.json', audit)
# Stop scheduling permanently before closing each already-owned simulation.
assert owned.same_process(identity)
os.kill(coordinator, signal.SIGKILL)
groups = {}
for pid, data in records.items():
    if pid != coordinator and data['pgid'] != record['pgid']:
        groups.setdefault(data['pgid'], []).append(data)
for pgid, members in groups.items():
    if any(owned.same_process(data) for data in members):
        os.killpg(pgid, signal.SIGINT)
time.sleep(3)
for pgid, members in groups.items():
    if any(owned.same_process(data) for data in members):
        os.killpg(pgid, signal.SIGKILL)
audit['remaining_verified_processes'] = [pid for pid, data in records.items()
    if owned.same_process(data)]
audit['closed_wall'] = time.time()
owned.atomic_json(job / 'orphan_cleanup.json', audit)
print(json.dumps(audit, indent=2))
assert not audit['remaining_verified_processes'], 'Owned cleanup incomplete'
