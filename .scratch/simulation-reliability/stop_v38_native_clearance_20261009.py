"""Request RTL on the owned failed native trial; preserve response and disarm evidence."""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
run = root / 'logs/reliability_reduced_v38_render_split_corridors_s20261003_20261008'
cfg = json.loads((run / 'configuration.json').read_text())
assert cfg['ros_domain'] == 30 and cfg['airframe'] == 'cad' and cfg['payload_fixture'] == 'loaded'
assert 'trial' not in cfg
watch = root / '.scratch/simulation-reliability/watch_v38_native_failed_trials_20261008.py'
tree = ast.parse(watch.read_text())
code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'request_code' for target in node.targets))
receipt = dict(reason='Independent live return clearance 0.6949338146612648 m at simulation stamp 422.746 is below unchanged 0.70 m acceptance requirement',
               qualified=False, domain=30, action='RTL service request; stack continues recording through actual disarm')
env = dict(os.environ, ROS_DOMAIN_ID='30', ROS_LOCALHOST_ONLY='1')
try:
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=15)
    receipt.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
except subprocess.TimeoutExpired as exc:
    def readable(value):
        return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
    receipt.update(returncode=None, timeout_s=15, stdout=readable(exc.stdout), stderr=readable(exc.stderr))
path = run / 'operator_clearance_stop.json'
if path.exists():
    count = len(list(run.glob('operator_clearance_stop_attempt_*.json'))) + 1
    path = run / f'operator_clearance_stop_attempt_{count}.json'
path.write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt), flush=True)
if 'mode_sent=True' not in receipt['stdout']:
    raise SystemExit(1)
