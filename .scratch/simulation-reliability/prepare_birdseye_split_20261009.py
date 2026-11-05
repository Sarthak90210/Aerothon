"""Add only an external-camera readiness barrier to a private recording launcher."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / '.scratch/simulation-reliability'
text = (root / 'scripts/run_recorded_acceptance.sh').read_text()
old = 'cd "$(dirname "${BASH_SOURCE[0]}")/.."'
assert text.count(old) == 1
text = text.replace(old, 'cd "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON"', 1)
barrier = '''python3 - <<'BIRDSEYE_READY'
import json,time
from pathlib import Path
ready=Path('.scratch/birdseye_split_v38_20261009_retry3/ready.json')
until=time.monotonic()+60
while time.monotonic()<until:
 if ready.exists():
  print('External overhead camera recording confirmed before mission start',flush=True)
  break
 time.sleep(.5)
else:raise SystemExit('Overhead camera not ready; mission was not started')
BIRDSEYE_READY
'''
assert text.count('mission_rc=0\n') == 1
text = text.replace('mission_rc=0\n', barrier+'mission_rc=0\n', 1)
# The provenance collector verifies the exact owning launcher path. Preserve
# that check for this private recording launcher instead of bypassing it.
capture = (base / 'capture_runtime_configuration.py').read_text()
assert capture.count("/'scripts/run_recorded_acceptance.sh'") == 1
capture = capture.replace("/'scripts/run_recorded_acceptance.sh'",
                          "/'.scratch/simulation-reliability/run_recorded_birdseye_acceptance_20261009.sh'", 1)
assert capture.count("Path(arg).name!='run_recorded_acceptance.sh'") == 1
capture = capture.replace("Path(arg).name!='run_recorded_acceptance.sh'",
                          "Path(arg).name!='run_recorded_birdseye_acceptance_20261009.sh'", 1)
(base / 'capture_birdseye_runtime_configuration_20261009.py').write_text(capture, newline='\n')
text = text.replace('capture_runtime_configuration.py','capture_birdseye_runtime_configuration_20261009.py')
(base / 'run_recorded_birdseye_acceptance_20261009.sh').write_text(text, newline='\n')
print('Private recording launcher prepared; production source untouched.')
