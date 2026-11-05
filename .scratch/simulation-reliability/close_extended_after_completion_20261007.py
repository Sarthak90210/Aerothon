"""Wait for owned batch closure, then verify all frozen evidence bytes."""
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[2]
path = root/'logs/reliability_command_deadline_extended_navigation_20261007/report.json'
while True:
    report = json.loads(path.read_text())
    if report.get('finished_wall'):
        break
    time.sleep(5)
raise SystemExit(subprocess.run(['/usr/bin/python3',
    '.scratch/simulation-reliability/close_command_deadline_extended_batch_20261007.py'], cwd=root).returncode)
