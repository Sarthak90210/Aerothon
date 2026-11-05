"""Safely close the owned native trial after recorded qualification is lost."""
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
run = root/'logs/reliability_reduced_v16_render_split_corridors_s20261003_20261008'
cfg = json.loads((run/'configuration.json').read_text())
assert cfg['ros_domain'] == 30 and cfg['airframe'] == 'cad' and cfg['payload_fixture'] == 'loaded'
rows=[]
for line in (run/'onboard.jsonl').read_text().splitlines():
    try: rows.append(json.loads(line))
    except ValueError: pass
last=rows[-1]
assert last['flight']['data']['connected'] and last['flight']['data']['armed']
tree=ast.parse((root/'.scratch/simulation-reliability/watch_v16_native_failed_trials_20261008.py').read_text())
code=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='request_code' for t in node.targets))
env=dict(os.environ,ROS_DOMAIN_ID='30',ROS_LOCALHOST_ONLY='1')
receipt=dict(reason='18 recorded hook target-floor contacts fail unchanged qualification evidence requirements; safe close for diagnosis',stamp=last['stamp'],domain=30)
result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=15)
receipt.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
with (run/'operator_stop.json').open('x') as f: json.dump(receipt,f,indent=2)
print(json.dumps(receipt),flush=True)
assert result.returncode == 0 and 'mode_sent=True' in result.stdout
