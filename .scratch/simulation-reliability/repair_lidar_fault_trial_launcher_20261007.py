"""Preserve the CRLF setup failure and prepare a separate LF launcher retry."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
here = Path(__file__).parent
old = root/'logs/reliability_lidar_fault_continuity_trials_owned_20261007'
script = here/'run_lidar_fault_continuity_trials_20261007.sh'
(old/'failed_crlf_launcher.sh').write_bytes(script.read_bytes())
assert not (root/'logs/reliability_lidar_fault_continuity_navigation_20261007').exists()
replacement = 'reliability_lidar_fault_continuity_trials_retry1_owned_20261007'
text = script.read_text().replace(old.name, replacement)
with (here/'run_lidar_fault_continuity_trials_retry1_20261007.sh').open('xb') as stream:
    stream.write(text.encode())
runner = here/'run_lidar_fault_continuity_batch_20261007.py'
(old/'before_retry_batch_runner.py').write_bytes(runner.read_bytes())
runner.write_bytes(runner.read_text().replace(old.name, replacement).encode())
print('Setup failure preserved; no physical trial was executed')
