"""Stop one verified stale helper; never signal a flight or recorder."""
import os,signal
from pathlib import Path
pid=1313
path=Path(f'/proc/{pid}/cmdline')
if path.exists():
    args=path.read_bytes().split(bytes([0]))
    assert args[:2]==[b'python3',b'.scratch/simulation-reliability/watch_v17_native_failed_trials_20261008.py'],args
    os.kill(pid,signal.SIGTERM)
    print('Closed stale V17 watchdog; no flight process touched')
