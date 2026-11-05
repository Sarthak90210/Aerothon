"""Start the four remaining native acceptances only after split is closed PASS."""
import json
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
split = root / 'logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008/summary.json'
while True:
    if split.exists():
        try:
            summary = json.loads(split.read_text())
        except ValueError:
            time.sleep(2)
            continue
        if summary.get('acceptance_pass') is not True:
            raise SystemExit('Split acceptance failed; dependent rendered runs not started')
        break
    time.sleep(2)
print('Split acceptance PASS; starting four remaining native courses', flush=True)
subprocess.run(['bash', str(root / '.scratch/simulation-reliability/run_reduced_v16_remaining_rendered_20261008.sh')], check=True, cwd=root)
